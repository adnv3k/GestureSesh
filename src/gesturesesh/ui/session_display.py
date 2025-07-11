# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '.\ui\display_session.ui'
#
# Created by: PyQt5 UI code generator 5.15.4
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


import sys
from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_session_display(object):
    def setupUi(self, session_display):
        session_display.setObjectName("session_display")
        session_display.resize(575, 720)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(session_display.sizePolicy().hasHeightForWidth())
        session_display.setSizePolicy(sizePolicy)
        session_display.setMinimumSize(QtCore.QSize(575, 1))
        session_display.setMaximumSize(QtCore.QSize(16777215, 16777215))
        font = QtGui.QFont()
        font.setPointSize(15)
        font.setBold(True)
        font.setWeight(75)
        session_display.setFont(font)
        session_display.setWindowTitle("")
        icon = QtGui.QIcon()
        icon.addPixmap(
            QtGui.QPixmap(":/icons/icons/brush.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        session_display.setWindowIcon(icon)
        session_display.setStyleSheet("background: rgb(24,43,59)")
        self.verticalLayout = QtWidgets.QVBoxLayout(session_display)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.image_display = QtWidgets.QLabel(session_display)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.image_display.sizePolicy().hasHeightForWidth()
        )
        self.image_display.setSizePolicy(sizePolicy)
        self.image_display.setMinimumSize(QtCore.QSize(1, 1))
        self.image_display.setStyleSheet("background: rgb(30,56,78); border: none;")
        self.image_display.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.image_display.setFrameShadow(QtWidgets.QFrame.Plain)
        self.image_display.setText("")
        self.image_display.setScaledContents(False)
        self.image_display.setAlignment(QtCore.Qt.AlignCenter)
        self.image_display.setObjectName("image_display")
        self.verticalLayout.addWidget(self.image_display)
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setSpacing(0)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.session_info = QtWidgets.QLabel(session_display)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.session_info.sizePolicy().hasHeightForWidth())
        self.session_info.setSizePolicy(sizePolicy)
        self.session_info.setMaximumSize(QtCore.QSize(16777215, 32*2))
        font = QtGui.QFont()
        font.setFamily(
            "Apple SD Gothic Neo"
            if sys.platform == "darwin"
            else "MS Shell Dlg 2" if sys.platform.startswith("win") else "Noto Sans CJK"
        )
        font.setPointSize(15)
        font.setBold(True)
        font.setWeight(75)
        self.session_info.setFont(font)
        self.session_info.setCursor(QtGui.QCursor(QtCore.Qt.IBeamCursor))
        self.session_info.setAutoFillBackground(False)
        self.session_info.setStyleSheet('color: "white"')
        self.session_info.setTextInteractionFlags(
            QtCore.Qt.LinksAccessibleByMouse | QtCore.Qt.TextSelectableByMouse
        )
        self.session_info.setObjectName("session_info")
        self.horizontalLayout_4.addWidget(self.session_info)
        spacerItem = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum
        )
        self.horizontalLayout_4.addItem(spacerItem)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setSpacing(1)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        # Consistent size policy and minimum size for all image modification buttons
        mod_button_size_policy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
        )
        mod_button_min_size = QtCore.QSize(50, 0)
        # Grayscale button
        self.grayscale_button = QtWidgets.QPushButton(session_display)
        mod_button_size_policy.setHeightForWidth(
            self.grayscale_button.sizePolicy().hasHeightForWidth()
        )
        self.grayscale_button.setSizePolicy(mod_button_size_policy)
        self.grayscale_button.setMinimumSize(mod_button_min_size)
        self.grayscale_button.setMouseTracking(False)
        self.grayscale_button.setFocusPolicy(QtCore.Qt.NoFocus)
        self.grayscale_button.setStyleSheet("background: rgb(119, 153, 146);")
        self.grayscale_button.setText("")
        icon1 = QtGui.QIcon()
        icon1.addPixmap(
            QtGui.QPixmap(":/icons/icons/grayscale.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        self.grayscale_button.setIcon(icon1)
        self.grayscale_button.setIconSize(QtCore.QSize(24, 24))
        self.grayscale_button.setCheckable(True)
        self.grayscale_button.setObjectName("grayscale_button")
        self.horizontalLayout_2.addWidget(self.grayscale_button, 0, QtCore.Qt.AlignBottom)
        # Flip horizontal button
        self.flip_horizontal_button = QtWidgets.QPushButton(session_display)
        mod_button_size_policy.setHeightForWidth(
            self.flip_horizontal_button.sizePolicy().hasHeightForWidth()
        )
        self.flip_horizontal_button.setSizePolicy(mod_button_size_policy)
        self.flip_horizontal_button.setMinimumSize(mod_button_min_size)
        self.flip_horizontal_button.setMouseTracking(False)
        self.flip_horizontal_button.setFocusPolicy(QtCore.Qt.NoFocus)
        self.flip_horizontal_button.setStyleSheet("background: rgb(119, 153, 146);")
        self.flip_horizontal_button.setText("")
        icon2 = QtGui.QIcon()
        icon2.addPixmap(
            QtGui.QPixmap(":/icons/icons/flip horizontal.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        self.flip_horizontal_button.setIcon(icon2)
        self.flip_horizontal_button.setIconSize(QtCore.QSize(24, 24))
        self.flip_horizontal_button.setCheckable(True)
        self.flip_horizontal_button.setObjectName("flip_horizontal_button")
        self.horizontalLayout_2.addWidget(self.flip_horizontal_button, 0, QtCore.Qt.AlignBottom)
        # Flip vertical button
        self.flip_vertical_button = QtWidgets.QPushButton(session_display)
        mod_button_size_policy.setHeightForWidth(
            self.flip_vertical_button.sizePolicy().hasHeightForWidth()
        )
        self.flip_vertical_button.setSizePolicy(mod_button_size_policy)
        self.flip_vertical_button.setMinimumSize(mod_button_min_size)
        self.flip_vertical_button.setMouseTracking(False)
        self.flip_vertical_button.setFocusPolicy(QtCore.Qt.NoFocus)
        self.flip_vertical_button.setStyleSheet("background: rgb(119, 153, 146);")
        self.flip_vertical_button.setText("")
        icon3 = QtGui.QIcon()
        icon3.addPixmap(
            QtGui.QPixmap(":/icons/icons/flip vertical.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        self.flip_vertical_button.setIcon(icon3)
        self.flip_vertical_button.setIconSize(QtCore.QSize(24, 24))
        self.flip_vertical_button.setCheckable(True)
        self.flip_vertical_button.setObjectName("flip_vertical_button")
        self.horizontalLayout_2.addWidget(self.flip_vertical_button, 0, QtCore.Qt.AlignBottom)
        self.horizontalLayout_2.setAlignment(QtCore.Qt.AlignBottom)
        self.horizontalLayout_4.addLayout(self.horizontalLayout_2)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setSpacing(1)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.previous_image = QtWidgets.QPushButton(session_display)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.previous_image.sizePolicy().hasHeightForWidth()
        )
        self.previous_image.setSizePolicy(sizePolicy)
        self.previous_image.setMinimumSize(QtCore.QSize(50, 0))
        self.previous_image.setMouseTracking(False)
        self.previous_image.setFocusPolicy(QtCore.Qt.NoFocus)
        self.previous_image.setStyleSheet("background: rgb(119, 153, 146);")
        self.previous_image.setText("")
        icon4 = QtGui.QIcon()
        icon4.addPixmap(
            QtGui.QPixmap(":/icons/icons/arrow left.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        self.previous_image.setIcon(icon4)
        self.previous_image.setIconSize(QtCore.QSize(24, 24))
        self.previous_image.setObjectName("previous_image")
        self.horizontalLayout.addWidget(self.previous_image, 0, QtCore.Qt.AlignBottom)
        self.pause_timer = QtWidgets.QPushButton(session_display)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pause_timer.sizePolicy().hasHeightForWidth())
        self.pause_timer.setSizePolicy(sizePolicy)
        self.pause_timer.setMinimumSize(QtCore.QSize(50, 0))
        self.pause_timer.setMouseTracking(False)
        self.pause_timer.setFocusPolicy(QtCore.Qt.NoFocus)
        self.pause_timer.setStyleSheet("background: rgb(119, 153, 146);")
        self.pause_timer.setText("")
        icon5 = QtGui.QIcon()
        icon5.addPixmap(
            QtGui.QPixmap(":/icons/icons/Pause.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        self.pause_timer.setIcon(icon5)
        self.pause_timer.setIconSize(QtCore.QSize(24, 24))
        self.pause_timer.setObjectName("pause_timer")
        self.horizontalLayout.addWidget(self.pause_timer, 0, QtCore.Qt.AlignBottom)
        self.stop_session = QtWidgets.QPushButton(session_display)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.stop_session.sizePolicy().hasHeightForWidth())
        self.stop_session.setSizePolicy(sizePolicy)
        self.stop_session.setMinimumSize(QtCore.QSize(50, 0))
        self.stop_session.setMouseTracking(False)
        self.stop_session.setFocusPolicy(QtCore.Qt.NoFocus)
        self.stop_session.setStyleSheet("background: rgb(119, 153, 146);")
        self.stop_session.setText("")
        icon6 = QtGui.QIcon()
        icon6.addPixmap(
            QtGui.QPixmap(":/icons/icons/Square.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        self.stop_session.setIcon(icon6)
        self.stop_session.setIconSize(QtCore.QSize(24, 24))
        self.stop_session.setObjectName("stop_session")
        self.horizontalLayout.addWidget(self.stop_session, 0, QtCore.Qt.AlignBottom)
        self.next_image = QtWidgets.QPushButton(session_display)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.next_image.sizePolicy().hasHeightForWidth())
        self.next_image.setSizePolicy(sizePolicy)
        self.next_image.setMinimumSize(QtCore.QSize(50, 0))
        self.next_image.setMouseTracking(False)
        self.next_image.setFocusPolicy(QtCore.Qt.NoFocus)
        self.next_image.setStyleSheet("background: rgb(119, 153, 146);")
        self.next_image.setText("")
        icon7 = QtGui.QIcon()
        icon7.addPixmap(
            QtGui.QPixmap(":/icons/icons/arrow right.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off,
        )
        self.next_image.setIcon(icon7)
        self.next_image.setIconSize(QtCore.QSize(24, 24))
        self.next_image.setObjectName("next_image")
        self.horizontalLayout.addWidget(self.next_image, 0, QtCore.Qt.AlignBottom)
        self.horizontalLayout_4.addLayout(self.horizontalLayout)
        spacerItem1 = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.horizontalLayout_4.addItem(spacerItem1)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.timer_display = QtWidgets.QLabel(session_display)
        self.timer_display.setMinimumSize(QtCore.QSize(61, 21))
        self.timer_display.setMaximumSize(QtCore.QSize(16777215, 32))
        font = QtGui.QFont()
        font.setFamily(
            "Apple SD Gothic Neo"
            if sys.platform == "darwin"
            else "MS Shell Dlg 2" if sys.platform.startswith("win") else "Noto Sans CJK"
        )
        font.setPointSize(15)
        font.setBold(True)
        font.setItalic(False)
        font.setWeight(75)
        self.timer_display.setFont(font)
        self.timer_display.setStyleSheet("color: 'white';")
        self.timer_display.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.timer_display.setFrameShadow(QtWidgets.QFrame.Plain)
        self.timer_display.setLineWidth(1)
        self.timer_display.setAlignment(QtCore.Qt.AlignCenter)
        self.timer_display.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse)
        self.timer_display.setObjectName("timer_display")
        self.horizontalLayout_3.addWidget(self.timer_display)
        self.horizontalLayout_4.addLayout(self.horizontalLayout_3)
        self.verticalLayout.addLayout(self.horizontalLayout_4)

        self.retranslateUi(session_display)
        QtCore.QMetaObject.connectSlotsByName(session_display)

    def retranslateUi(self, session_display):
        _translate = QtCore.QCoreApplication.translate
        self.session_info.setText(_translate("session_display", "{session info}"))
        self.grayscale_button.setToolTip(
            _translate(
                "session_display",
                "Grayscale<br><span style='font-weight:650;'>G</span>",
            )
        )
        self.grayscale_button.setShortcut(_translate("session_display", "G"))
        self.flip_horizontal_button.setToolTip(
            _translate(
                "session_display",
                "Flip horizontal<br><span style='font-weight:650;'>H</span>",
            )
        )
        self.flip_horizontal_button.setShortcut(_translate("session_display", "H"))
        self.flip_vertical_button.setToolTip(
            _translate(
                "session_display",
                "Flip vertical<br><span style='font-weight:650;'>V</span>",
            )
        )
        self.flip_vertical_button.setShortcut(_translate("session_display", "V"))
        self.previous_image.setToolTip(
            _translate(
                "session_display",
                "Previous image<br><span style='font-weight:650;'>Left arrow"
                " key</span>",
            )
        )
        self.previous_image.setShortcut(_translate("session_display", "Left"))
        self.pause_timer.setToolTip(
            _translate(
                "session_display",
                "Pause Timer<br><span style='font-weight:650;'>Space</span>",
            )
        )
        self.pause_timer.setShortcut(_translate("session_display", "Space"))
        self.stop_session.setToolTip(
            _translate(
                "session_display",
                "Stop Session. Closes window.<br><span"
                " style='font-weight:650;'>Esc</span>",
            )
        )
        self.stop_session.setShortcut(_translate("session_display", "Esc"))
        self.next_image.setToolTip(
            _translate(
                "session_display",
                "Next Image<br><span style='font-weight:650;'>Right arrow key</span>",
            )
        )
        self.next_image.setShortcut(_translate("session_display", "Right"))
        self.timer_display.setText(_translate("session_display", "00:00"))
