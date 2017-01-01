#!/usr/bin/env python

#  Copyright (c) 2016, Aeva M. Palecek

#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.


import os
import re
import sys
import time
from threading import Thread
from multiprocessing import Pool, cpu_count
import gi
from gi.repository import GLib, Gtk, Gdk, GObject
from nw2png import convert_to_png
from nw2tiled import convert_to_tmx


def run_jobs(window, converter, jobs):
    scope = {
        "processed" : 0
    }

    def job_callback(result):
        scope["processed"] += 1
        GLib.idle_add(window.advance_progress, scope["processed"])

    start = time.time()
    pool = Pool(max(cpu_count(), 2))
    for job in jobs:
        job_callback(converter(*job))
        #pool.apply_async(converter, job, callback=job_callback)

    pool.close()
    pool.join()
    GLib.idle_add(window.conclude_progress, time.time()-start)

    
class ConverterWindow(object):
    def __init__(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file("gui_layout.glade")
        self.builder.connect_signals(self)

        self.levels = set()
        self.levels_store = self.builder.get_object("level_path_store")
        self.levels_view = self.builder.get_object("level_tree_view")
        self.setup_treeview()
        
        self.window = self.builder.get_object("main_window")
        self.window.show_all()
        self.about_popup = self.builder.get_object("about_popup")
        self.progress_popup = self.builder.get_object("progress_popup")
        self.progress_label = self.builder.get_object("progress_label")
        self.progress_bar = self.builder.get_object("progressbar")
        self.setup_filters()
        self.setup_drag_n_drop()
        self.setup_working_dirs()

    def setup_treeview(self):
        column = Gtk.TreeViewColumn('')
        icon_cell = Gtk.CellRendererPixbuf()
        icon_cell.set_alignment(0.0, 0.75)
        text_cell = Gtk.CellRendererText()
        text_cell.set_property("ellipsize", 3)
        text_cell.set_padding(6, 0)
        column.pack_start(icon_cell, False)
        column.pack_end(text_cell, True)
        column.add_attribute(icon_cell, "icon_name", 0)
        column.add_attribute(text_cell, "text", 1)
        self.levels_view.append_column(column)

    def setup_drag_n_drop(self):
        targets = [("text/uri-list", 0, 0)]
        self.levels_view.enable_model_drag_dest(targets, Gdk.DragAction.DEFAULT)

    def setup_filters(self):
        img_filter = Gtk.FileFilter()
        img_filter.set_name("Image files")
        img_filter.add_mime_type("image/*")
        pics_chooser = self.builder.get_object("pics1_chooser")
        pics_chooser.add_filter(img_filter)

    def setup_working_dirs(self):
        self.working_dir = path = os.getcwd()
        self.builder.get_object("pics1_chooser").set_current_folder(path)
        self.builder.get_object("search_path_chooser").set_current_folder(path)
        self.builder.get_object("output_path_chooser").set_current_folder(path)

    def find_common_path(self, pathset):
        def cut(path):
            tail, head = os.path.split(path)
            if tail == path:
                return []
            else:
                return cut(tail) + [head]            
        def clean(path):
            return tuple(cut(os.path.abspath(path)))
        paths = map(clean, pathset)
        return "/" + os.path.join(*os.path.commonprefix(paths))

    def refresh_levels_view(self):
        dir_icon = "folder"
        doc_icon = "emblem-documents"

        all_levels = list(self.levels)
        all_levels.sort()
        all_paths = set([path for path, level in all_levels])

        self.levels_store.clear()

        if len(all_paths) == 1:
            # don't bother with nesting
            for path, level in all_levels:
                self.levels_store.append(None, [doc_icon, level])
        else:
            common_path = self.find_common_path(all_paths)
            path_iters = {}
            for path, level in all_levels:
                nice_path = os.path.relpath(path, common_path)
                if not path_iters.has_key(path):
                    path_iters[path] = self.levels_store.append(
                        None, [dir_icon, nice_path])
                self.levels_store.append(path_iters[path], [doc_icon, level])

    def add_level(self, path):
        #extensions = r'.+\.(nw|graal|zelda)$'
        extensions = r'.+\.(nw)$'
        if os.path.isdir(path):
            for base_dir, dirs, files in os.walk(path):
                for file_ in files:
                    path = os.path.join(base_dir, file_)
                    if re.match(extensions, path):
                        self.add_level(path)
        else:
            path, head = os.path.split(path)
            level = (os.path.abspath(path), head)
            if re.match(extensions, head):
                self.levels.add(level)

    def start_progress(self):
        self.window.set_sensitive(False)
        self.progress_popup.show_all()
        self.progress_bar.set_fraction(0.0)
        self.progress_label.set_text(
            'Converting levels... (0/{0})'.format(
                len(self.levels)))

    def advance_progress(self, completed):
        if completed > len(self.levels):
            return
        self.progress_bar.set_fraction(completed / float(len(self.levels)))
        self.progress_label.set_text(
            "Converting levels... ({0}/{1})".format(
                completed+1,
                len(self.levels)))

    def conclude_progress(self, elapsed_time):
        self.progress_popup.hide()

        message = "All done!\nConverted {0} files in {1} seconds.".format(
            len(self.levels), round(elapsed_time, 2))

        pop = Gtk.MessageDialog(
            self.window,
            0, Gtk.MessageType.INFO,
            Gtk.ButtonsType.CLOSE, message)
        pop.run()
        pop.destroy()

        self.window.set_sensitive(True)
        self.clear_levels()

    ### the methods below are signal handlers

    def image_search_changed(self, *args, **kargs):
        chooser = self.builder.get_object("pics1_chooser")
        if not chooser.get_filename():
            search = self.builder.get_object("search_path_chooser").get_filename()
            chooser.set_current_folder(search)
        
    def show_about(self, *args, **kargs):
        self.about_popup.run()
        self.about_popup.hide()

    def show_add_files(self, *args, **kargs):
        chooser = Gtk.FileChooserDialog(
            "Select Level Files for Conversion", self.window,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

        level_filter = Gtk.FileFilter()
        level_filter.set_name("Graal level (*.nw)")
        level_filter.add_pattern("*.nw")
        chooser.add_filter(level_filter)
        chooser.set_select_multiple(True)
        chooser.set_current_folder(self.working_dir)

        response = chooser.run()
        if response == Gtk.ResponseType.OK:
            paths = chooser.get_filenames()
            for path in paths:
                self.add_level(path)
            self.refresh_levels_view()

            path = paths[-1]
            if os.path.isdir(path):
                self.working_dir = path
            else:
                self.working_dir = os.path.split(path)[0]
                
        chooser.destroy()

    def clear_levels(self, *args, **kargs):
        self.levels.clear()
        self.levels_store.clear()

    def file_drop_event(self, widget, drag_context, x, y, data, info, time):
        uris = data.get_uris()
        prefix = "file://"
        for uri in uris:
            if uri.startswith(prefix):
                path = uri[len(prefix):]
                self.add_level(path)
        self.refresh_levels_view()
        
    def run_converter(self, *args, **kargs):
        tmx_button = self.builder.get_object("tmx_radio")
        png_button = self.builder.get_object("png_radio")
        converter = None
        suffix = None
        if tmx_button.get_active():
            converter = convert_to_tmx
            suffix = "tmx"
        if png_button.get_active():
            converter = convert_to_png
            suffix = "png"

        self.levels
        tileset = self.builder.get_object("pics1_chooser").get_filename()
        search = self.builder.get_object("search_path_chooser").get_filename()
        out = self.builder.get_object("output_path_chooser").get_filename()

        if not tileset or not search or not out:
            return

        self.start_progress()
        processed = 0
        jobs = []
        for path, level in self.levels:
            level_path = os.path.join(path, level)
            out_path = os.path.join(out, level) + '.' + suffix
            jobs.append((level_path, tileset, search, out_path))
        Thread(target=run_jobs, args=(self, converter, jobs)).start()

    def shutdown(self, *args, **kargs):
        Gtk.main_quit()

        
if __name__ == "__main__":
    Gtk.init()
    converter = ConverterWindow()
    for path in sys.argv[0:]:
        converter.add_level(path)
    converter.refresh_levels_view()
    Gtk.main()
