import os
import collections
import datetime
import shutil
import subprocess

from uitools.qt import Q


PlayblastInfo = collections.namedtuple('PlayblastInfo', (
    'name',
    'directory',
    'first_frame',
    'user_category',
    'created_at',
    'audio',
    'maya_file'
))

def parse_audio_txt(path):
    audio = None
    maya_file = None
    frame_rate = 24
    with open(path) as f:
        for line in f.readlines():
            if line.startswith('#'):
                continue
            line = line.rstrip()

            if line.lower() == 'ntsc':
                frame_rate = 29.97

            if os.path.exists(line):
                name, ext = os.path.splitext(line)
                if ext.lower() in ('.wav', '.aif'):
                    audio = line
                if ext.lower() in ('.mb', '.ma'):
                    maya_file = line

    return audio, maya_file, frame_rate

class PlayblastThumbnail(Q.Label):
    
    def __init__(self, path):
        self._path = path
        self._loaded = False
        super(PlayblastThumbnail, self).__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setPixmap(Q.Pixmap(self._path).scaled(100, 57, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self._loaded = True

    def sizeHint(self):
        if self._loaded:
            return self.pixmap().size()
        else:
            return Q.Size(100, 57)

class PlayblastTable(Q.TableWidget):
    refresh = Q.pyqtSignal()

    def __init__(self, parent = None):
        super(PlayblastTable, self).__init__(parent)
        self.setColumnCount(3)
        self.setColumnWidth(0, 100)
        self.verticalHeader().hide()
        self.horizontalHeader().setStretchLastSection(True)
        self.setHorizontalHeaderLabels(['First Frame', 'Name', 'Creation Time'])
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(self.SelectRows)
        self.setSortingEnabled(True)
        self.sortItems(2, Qt.DescendingOrder)
        self.setEditTriggers(Q.AbstractItemView.NoEditTriggers)
        self.itemDoubleClicked .connect(lambda x: self.flipbook_playblast())

    def add_playblasts(self, playblasts):
        for playblast in sorted(playblasts, key = lambda pb: (' None' if pb.user_category == 'none' else pb.user_category, pb.name)):
            row = self.rowCount()
            self.setRowCount(row + 1)
            self.setRowHeight(row, 57)

            thumb = PlayblastThumbnail(playblast.first_frame)
            thumb.playblast = playblast
            self.setCellWidget(row, 0, thumb)

            name = Q.TableWidgetItem(playblast.name)
            self.setItem(row, 1, name)

            date = Q.TableWidgetItem(playblast.created_at.isoformat(' '))
            self.setItem(row, 2, date)

    def contextMenuEvent(self, event):
        menu = Q.Menu(self)
        flipbook_action = menu.addAction("Flipbook")
        flipbook_action.triggered.connect(self.flipbook_playblast)
        qt_action = menu.addAction("Make Quicktime")
        qt_action.triggered.connect(self.make_quicktime)
        refresh_action = menu.addAction("Refresh")
        refresh_action.triggered.connect(self.refresh.emit)
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(self.delete_playblasts)
        action = menu.exec_(event.globalPos())

    def current_playblast(self):
        row = self.currentRow()
        thumb = self.cellWidget(row, 0) if row is not None else None
        playblast = thumb and thumb.playblast
        return playblast

    def current_path(self):
        playblast = self.current_playblast()
        path = playblast and playblast.directory
        return path if path and os.path.exists(path) else None

    def delete_playblasts(self):
        rows = []
        for item in self.selectedItems():
            if not item.row() in rows:
                rows.append(item.row())

        for row in reversed(sorted(rows)):
            dirname = None
            thumb = self.cellWidget(row, 0) if row is not None else None
            if thumb and thumb.playblast and thumb.playblast.directory and os.path.exists(thumb.playblast.directory):
                dirname = thumb.playblast.directory

            print "rm", dirname, row
            self.removeRow(row)
            if dirname:
                shutil.rmtree(dirname)

    def flipbook_playblast(self):
        playblast = self.current_playblast()

        cmd = ['rv', '[', os.path.join(playblast.directory, '*.jpg'), '-fps', str(24), ']']
        if playblast.audio:
            cmd.extend(['-over', '[', playblast.audio, ']'])

        # fix for launching rv from maya on mac
        # http://www.tweaksoftware.com/static/documentation/rv/current/html/maya_tools_help.html#_osx_maya_2014
        env = dict(os.environ)
        if 'QT_MAC_NO_NATIVE_MENUBAR' in env:
            del env['QT_MAC_NO_NATIVE_MENUBAR']

        print subprocess.list2cmdline(cmd)
        proc = subprocess.Popen(cmd, env = env)

    def make_quicktime(self):
        playblast = self.current_playblast()

        cmd = ['make_quicktime', playblast.first_frame]

        if playblast.audio:
            cmd.extend(['--audio', playblast.audio])

        if playblast.maya_file:
            cmd.extend(['--shotdir', playblast.maya_file])

        print subprocess.list2cmdline(cmd)
        subprocess.Popen(cmd)

class Picker(Q.TabWidget):
    
    pathChanged = Q.pyqtSignal(object)
    
    def __init__(self, parent = None, selection_mode = Q.TableWidget.SingleSelection,):
        super(Picker, self).__init__(parent)
        
        self._playblasts = []
        self._selection_mode = selection_mode
        self._find_legacy_playblasts()
        self._tables_by_name = {}
        self._setup_ui()

    
    def _setup_ui(self):
        self.currentChanged.connect(self._current_tab_changed)
        tables = self._tables_by_name
        for playblast in sorted(self._playblasts,
            key=lambda pb: (' None' if pb.user_category == 'none' else pb.user_category, pb.name)
        ):
            if playblast.user_category not in tables:

                table = PlayblastTable()
                table.itemSelectionChanged.connect(self._table_selection_changed)
                table.refresh.connect(self.refresh)
                if self._selection_mode:
                    table.setSelectionMode(self._selection_mode)
                tables[playblast.user_category] = table                
                self.addTab(table, "Playblasts" if playblast.user_category == "none" else playblast.user_category.title())

            table = tables[playblast.user_category]
            table.add_playblasts([playblast])
        
        for table in tables.itervalues():
            table.resizeColumnToContents(1)
            table.resizeColumnToContents(2)

    def refresh(self):
        for table in self._tables_by_name.itervalues():
            table.clearContents()
            table.setRowCount(0)
        self._playblasts = []
        self._find_legacy_playblasts()
        self._setup_ui()

    def _find_legacy_playblasts(self):

        # This is the folder that they are stored in.
        if not os.path.exists('/var/tmp/srv_playblast'):
            return

        for name in os.listdir('/var/tmp/srv_playblast'):

            directory = os.path.join('/var/tmp/srv_playblast', name)

            # Try to grab the first frame.
            try:
                file_names = os.listdir(directory)
            except OSError as e:
                if e.errno == 20: # Not a folder.
                    continue
                raise

            frame_gen = (x for x in sorted(file_names) if os.path.splitext(x)[1] in ('.jpg', '.jpeg'))
            first_frame = next(frame_gen, None)
            if first_frame is None:
                continue

            audio = None
            maya_file = None
            audio_text = next((x for x in sorted(file_names) if os.path.splitext(x)[1] in ('.txt',)))
            if audio_text:
                audio, maya_file, frame_rate = parse_audio_txt(os.path.join(directory, audio_text))

            first_frame = os.path.join(directory, first_frame)

            user_category_path = os.path.join(directory, 'approval_status')
            user_category = open(user_category_path).read() if os.path.exists(user_category_path) else None
            user_category = str(user_category).lower()

            self._playblasts.append(PlayblastInfo(
                name = name,
                directory = directory,
                user_category = user_category,
                first_frame = first_frame,
                created_at = datetime.datetime.fromtimestamp(os.path.getctime(first_frame)),
                audio = audio,
                maya_file = maya_file
            ))

    def autoSetMinimumWidth(self):
        width = 0
        for table in self._tables_by_name.itervalues():
            width = max(width, sum(table.columnWidth(i) for i in xrange(table.columnCount())))
        if width:
            self.setMinimumWidth(width)
    
    def _table_selection_changed(self):
        path = self.currentPath()
        self.pathChanged.emit(path)
    
    def _current_tab_changed(self):
        path = self.currentPath()
        self.pathChanged.emit(path)
        
    def currentPath(self):
        table = self.currentWidget()
        return table.current_path()



if __name__ == '__main__':
    import sys
    app = Q.Application([])
    widget = Picker()
    widget.autoSetMinimumWidth()
    widget.show()
    widget.raise_()
    sys.exit(app.exec_())

