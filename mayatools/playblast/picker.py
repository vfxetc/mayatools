import os
import re
import glob
import collections
import datetime

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt


PlayblastInfo = collections.namedtuple('PlayblastInfo', (
    'name',
    'directory',
    'first_frame',
    'user_category',
    'created_at',
))


class PlayblastThumbnail(QtGui.QLabel):
    
    def __init__(self, path):
        self._path = path
        self._loaded = False
        super(PlayblastThumbnail, self).__init__()
        self.setAlignment(Qt.AlignCenter)
    
    def paintEvent(self, e):
        if not self._loaded:
            self.setPixmap(QtGui.QPixmap(self._path).scaled(100, 57, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self._loaded = True
        return super(PlayblastThumbnail, self).paintEvent(e)
    
    def sizeHint(self):
        if self._loaded:
            return self.pixmap().size()
        else:
            return QtCore.QSize(100, 57)


class Picker(QtGui.QTabWidget):
    
    pathChanged = QtCore.pyqtSignal(object)
    
    def __init__(self, parent=None):
        super(Picker, self).__init__(parent)
        
        self._playblasts = []
        self._find_legacy_playblasts()
        
        self._setup_ui()
    
    def _setup_ui(self):
        
        self.currentChanged.connect(self._current_tab_changed)
        
        self._tables_by_name = tables = {}
        for playblast in sorted(self._playblasts,
            key=lambda pb: (' None' if pb.user_category == 'none' else pb.user_category, pb.name)
        ):
            if playblast.user_category not in tables:
                
                table = QtGui.QTableWidget()
                table.setColumnCount(3)
                table.setColumnWidth(0, 100)
                table.verticalHeader().hide()
                table.horizontalHeader().setStretchLastSection(True)
                table.setHorizontalHeaderLabels(['First Frame', 'Name', 'Creation Time'])
                
                table.setSelectionMode(table.SingleSelection)
                table.setSelectionBehavior(table.SelectRows)
                table.setSortingEnabled(True)
                
                table.itemSelectionChanged.connect(self._table_selection_changed)
                
                tables[playblast.user_category] = table                
                self.addTab(table, "Playblasts" if playblast.user_category == "none" else playblast.user_category.title())
            
            table = tables[playblast.user_category]
            
            row = table.rowCount()
            table.setRowCount(row + 1)
            table.setRowHeight(row, 57)
            thumb = PlayblastThumbnail(playblast.first_frame)
            thumb.playblast = playblast
            table.setCellWidget(row, 0, thumb)
            
            name = QtGui.QTableWidgetItem(playblast.name)
            table.setItem(row, 1, name)

            date = QtGui.QTableWidgetItem(playblast.created_at.isoformat(' '))
            table.setItem(row, 2, date)
        
        for table in tables.itervalues():
            table.resizeColumnToContents(1)
            table.resizeColumnToContents(2)
    
    def _find_legacy_playblasts(self):
        
        # This is the folder that they are stored in.
        if not os.path.exists('/var/tmp/srv_playblast'):
            return
        
        for name in os.listdir('/var/tmp/srv_playblast'):
            
            directory = os.path.join('/var/tmp/srv_playblast', name)
            
            # Try to grab the first frame.
            file_names = os.listdir(directory)
            frame_gen = (x for x in sorted(file_names) if os.path.splitext(x)[1] in ('.jpg', '.jpeg'))
            first_frame = next(frame_gen, None)
            if first_frame is None:
                continue
            first_frame = os.path.join(directory, first_frame)
            
            user_category_path = os.path.join(directory, 'approval_status')
            user_category = open(user_category_path).read() if os.path.exists(user_category_path) else None
            user_category = str(user_category).lower()
            
            self._playblasts.append(PlayblastInfo(
                name=name,
                directory=directory,
                user_category=user_category,
                first_frame=first_frame,
                created_at=datetime.datetime.fromtimestamp(os.path.getctime(first_frame)),
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
        row = table and table.currentRow()
        thumb = table.cellWidget(row, 0) if row is not None else None
        path = thumb and thumb.playblast.directory
        return path if path and os.path.exists(path) else None


if __name__ == '__main__':
    
    app = QtGui.QApplication([])
    widget = Picker()
    widget.autoSetMinimumWidth()
    widget.show()
    widget.raise_()
    app.exec_()

