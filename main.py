#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import fsto
from threading import Thread
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject


# fs = FSApi('http://fs.to/video/cartoonserials/i4ELwBwDaJdYuWDPF0fo2oU-tetrad-smerti.html')
# movies = fs.search('Death Note')
# movie = movies[0]

# root = movie.get_root_folder()

# while True:
#     file_id = raw_input('Enter series id: ')
#     print root.items[0].items[0].items[0].items[0]
#     # print movie.get_file_url(file_id)


def main():
    Gdk.threads_init()
    api = fsto.FSApi()

    def bg(fn):
        def wrapper(*args, **kwargs):
            Thread(target=fn, args=args, kwargs=kwargs).start()
        return wrapper

    @bg
    def do_search_movies(query):
        movies = api.search(query)

        def search_cb():
            movies_store.clear()
            for movie in movies:
                movies_store.append((movie, movie.url, movie.title, movie.poster))
            combo.popup()

        # def search_cb(values):

        Gdk.threads_add_idle(0, search_cb)

    def on_movie_selected_cb(combobox):
        if combobox.get_active() != -1:
            movie, url, title, poster = movies_store[combobox.get_active()]

            do_load_folder_files(movie.get_root_folder())

        # window.set_sensitive(False)

    @bg
    def do_load_folder_files(folder, insert_at=None, expand=None):
        Gdk.threads_add_idle(0, lambda: window.set_sensitive(False))
        items = list(folder.items)

        def fetch_cb():
            if not insert_at:
                tree_store.clear()
            for folder in items:
                tree_store.append(insert_at, (folder, folder.title, False))
            if expand:
                tree.expand_row(expand, True)
            window.set_sensitive(True)
        Gdk.threads_add_idle(0, fetch_cb)

    @bg
    def on_item_selected_cb(treeview, path, column):
        tree_iter = tree_store.get_iter(path)
        value = tree_store.get_value(tree_iter, 0)
        is_loaded = tree_store.get_value(tree_iter, 2)
        if isinstance(value, fsto.FSFolder) and not is_loaded:
            do_load_folder_files(value, tree_iter, path)
        else:
            # print 'Playing file', value
            value.get_file_url()

    window = Gtk.Window()
    window.connect('destroy', Gtk.main_quit)

    vbox = Gtk.VBox()
    window.add(vbox)
    window.set_size_request(600, 400)

    # Movie search

    def on_combo_key_press_cb(combo, event):
        if event.string in ('\r', '\n'):
            do_search_movies(combo.get_text())

    combo = Gtk.ComboBoxText.new_with_entry()
    combo.get_child().connect('key_press_event', on_combo_key_press_cb)
    combo.connect('changed', on_movie_selected_cb)
    # combo.set_hexpand(True)
    vbox.pack_start(combo, False, True, 0)

    movies_store = Gtk.ListStore(GObject.TYPE_PYOBJECT, GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_STRING)
    combo.set_model(movies_store)
    combo.set_entry_text_column(2)

    # File list

    tree = Gtk.TreeView()
    tree_store = Gtk.TreeStore(GObject.TYPE_PYOBJECT, GObject.TYPE_STRING, GObject.TYPE_BOOLEAN)
    tree.set_model(tree_store)

    tree.connect('row-activated', on_item_selected_cb)

    renderer1 = Gtk.CellRendererText()
    column1 = Gtk.TreeViewColumn('Title', renderer1, text=1)
    tree.append_column(column1)

    vbox.pack_start(tree, True, True, 0)

    window.show_all()

    Gtk.main()


if __name__ == '__main__':
    main()
