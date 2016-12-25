
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
import gi
from gi.repository import Gtk, GObject
from nw2png import convert_to_png
from nw2tiled import convert_to_tmx


class ConverterWindow(object):
    def __init__(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file("gui_layout.glade")
        self.builder.connect_signals(self)

        self.levels = set()
        self.levels_store = self.builder.get_object("level_path_store")
        self.levels_view = self.builder.get_object("level_tree_view")

        renderer = Gtk.CellRendererText()
        renderer.set_property("ellipsize", 3)
        title_column = Gtk.TreeViewColumn("Tab Title", renderer, text=0)
        self.levels_view.append_column(title_column)
        
        self.window = self.builder.get_object("main_window")
        self.window.show_all()
        self.about_popup = self.builder.get_object("about_popup")
        self.chooser_popup = self.builder.get_object("file_chooser_popup")
        self.setup_filters()

    def setup_filters(self):
        level_filter = Gtk.FileFilter()
        level_filter.set_name("Graal level (*.nw)")
        level_filter.add_pattern("*.nw")
        img_filter = Gtk.FileFilter()
        img_filter.set_name("Image files")
        img_filter.add_mime_type("image/*")

        self.chooser_popup.add_filter(level_filter)
        pics_chooser = self.builder.get_object("pics1_chooser")
        pics_chooser.add_filter(img_filter)

    def refresh_levels_view(self):
        all_levels = list(self.levels)
        all_levels.sort()
        all_paths = set([path for path, level in all_levels])

        if len(all_paths) == 1:
            # don't bother with nesting
            for path, level in all_levels:
                self.levels_store.append(None, [level])
        else:
            self.levels_store.clear()
            path_iters = {}
            for path, level in all_levels:
                if not path_iters.has_key(path):
                    path_iters[path] = self.levels_store.append(None, [path])
                self.levels_store.append(path_iters[path], [level])

    def add_level(self, path):
        extensions = r'.+\.(nw|graal|zelda)$'
        if os.path.isdir(path):
            for base_dir, dirs, files in os.walk(path):
                for file_ in files:
                    path = os.path.join(base_dir, file_)
                    if re.match(extensions, path):
                        self.add_level(path)
        else:
            path, head = os.path.split(path)
            level = (os.path.abspath(path), head)
            self.levels.add(level)

    ### the methods below are signal handlers
        
    def show_about(self, *args, **kargs):
        self.about_popup.run()
        self.about_popup.hide()

    def show_add_files(self, *args, **kargs):
        self.chooser_popup.set_select_multiple(True)
        self.chooser_popup.run()
        self.chooser_popup.hide()
        for path in self.chooser_popup.get_filenames():
            self.add_level(path)
        self.refresh_levels_view()

    def clear_levels(self, *args, **kargs):
        self.levels.clear()
        self.levels_store.clear()

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

        for path, level in self.levels:
            level_path = os.path.join(path, level)
            out_path = os.path.join(out, level) + '.' + suffix
            converter(level_path, tileset, search, out_path)

    def shutdown(self, *args, **kargs):
        Gtk.main_quit()

        
if __name__ == "__main__":
    Gtk.init()
    browser = ConverterWindow()
    Gtk.main()
