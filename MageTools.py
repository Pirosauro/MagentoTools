import sublime
import sublime_plugin
import os
import threading
import shutil
import sys
from functools import partial


class MageToolsCommand(sublime_plugin.WindowCommand):

    def copy_to_clipboard_and_inform(self, data):
        sublime.set_clipboard(data)
        lines = len(data.split('\n'))
        self.window.status_message('Copied {} to clipboard'.format(
            '{} lines'.format(lines) if lines > 1 else '"{}"'.format(data)
        ))

    def get_path(self, paths):
        try:
            return paths[0]
        except IndexError:
            return self.window.active_view().file_name()

    def is_visible(self, paths):
        if paths:
            return len(paths) < 2
        return bool(self.window.active_view().file_name())

    @staticmethod
    def make_dirs_for(filename):
        destination_dir = os.path.dirname(filename)
        try:
            os.makedirs(destination_dir)
            return True
        except OSError:
            return False


class MageFilesMixin(object):

    def get_paths(self, paths):
        return paths or [self.get_path(paths)]

    def is_visible(self, paths):
        return bool(paths or self.window.active_view().file_name())


class MageToolsCopyCommand(MageFilesMixin, MageToolsCommand):

    _magento_root = False
    _magento_theme = False

    @property
    def magento_root(self):
        window = sublime.active_window()
        view = window.active_view()
        settings = view.settings()
        folders = window.project_data()['folders']

        for i in range(0, len(folders)):
            if 'magento_root' in folders[i]:
                self._magento_root = window.folders()[i]
                break

        if self._magento_root == False:
            self._magento_root = settings.get('magento_root', False)

        return self._magento_root

    @property
    def magento_theme(self):
        window = sublime.active_window()
        view = window.active_view()
        settings = view.settings()
        folders = window.project_data()['folders']

        for i in range(0, len(folders)):
            if 'magento_theme' in folders[i]:
                self._magento_theme = window.folders()[i]
                break

        if self._magento_theme == False:
            self._magento_theme = settings.get('magento_theme', False)

        return self._magento_theme

    def is_visible(self, paths):
        return bool(self.magento_root) and bool(self.magento_theme) and os.path.isdir(self.magento_root)

    def is_enabled(self, paths):
        source = self.get_path(paths)
        name, ext = os.path.splitext(os.path.split(source)[1])

        if ext is not '':
            while '.' in name:
                name, _ext = os.path.splitext(name)
                ext = _ext + ext

                if _ext is '':
                    break

        path = os.path.relpath(source, self.magento_root).split(os.sep)

        if path[0] == "vendor":
            base = path[0]
        elif path[0] == "app" and path[1] == "code":
            base = os.path.join(path[0], path[1])

        if ext in [".phtml", ".js", ".html", ".less", ".scss"] and base == "vendor":
            # module
            if path[2][:7] == "module-" and path[3] == "view":
                return True
            # theme
            elif path[2][:6] == "theme-":
                return True

        return False

    def run(self, paths):
        source = self.get_path(paths)
        input_panel = self.window.show_input_panel(
            'Duplicate As:',
            os.path.split(source)[1],
            partial(self.on_done, source),
            None,
            None
        )

        input_panel.sel().clear()
        # input_panel.sel().add(
        #     sublime.Region(0, len(initial_text) - (len(ext)))
        # )

    def on_done(self, source, destination):
        name, ext = os.path.splitext(os.path.split(source)[1])

        if ext is not '':
            while '.' in name:
                name, _ext = os.path.splitext(name)
                ext = _ext + ext

                if _ext is '':
                    break

        path = os.path.relpath(source, self.magento_root).split(os.sep)

        # module
        if path[2][:7] == "module-":
            theme_area = path[4] # frontend/adminhtml
            vendor_module = path[1].title()+"_"+path[2][7:].replace("-", " ").title().replace(" ", "")
            base, _ = os.path.split(os.path.join(self.magento_theme, vendor_module, os.path.join(*path[5:])))
            destination = os.path.join(base, destination)

            threading.Thread(
                target=self.copy,
                args=(source, destination)
            ).start()
        # theme
        elif path[2][:6] == "theme-":
            vendor_module = path[3]
            base, _ = os.path.split(os.path.join(self.magento_theme, vendor_module, os.path.join(*path[5:])))
            destination = os.path.join(base, destination)
            print(source)
            print(destination)

            # threading.Thread(
            #     target=self.copy,
            #     args=(source, destination)
            # ).start()

    def copy(self, source, destination):
        self.window.status_message(
            'Copying "{}" to "{}"'.format(source, destination)
        )

        self.make_dirs_for(destination)

        try:
            if os.path.isdir(source):
                shutil.copytree(source, destination)
            else:
                shutil.copy2(source, destination)
        except OSError as error:
            self.window.status_message(
                'Error copying: {error} ("{src}" to "{dst}")'.format(
                    src=source,
                    dst=destination,
                    error=error,
                )
            )

    def description(self):
        return 'Copy File'
