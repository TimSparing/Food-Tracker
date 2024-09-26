from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QSpacerItem,
    QSizePolicy,
    QDialog,
    QCalendarWidget,
    QGridLayout,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor, QIcon
import sys
import pyqtgraph as pg
import os
import sqlite3

ButtonWidth = 80
InputWidth = 125
Goal = 75


class CustomAxisItem(pg.AxisItem):
    """Tilts the x-axis labels"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # X-Axis labels tilt angle
        self.label_angle = -60

    def boundingRect(self):
        # Prevents the labels from disappearing near the edges
        rect = self.mapRectFromParent(self.geometry())

        tl = self.style["tickLength"]
        m = 200

        if self.orientation == "left":
            rect = rect.adjusted(0, -m, -min(0, tl), m)
        elif self.orientation == "right":
            rect = rect.adjusted(min(0, tl), -m, 0, m)
        elif self.orientation == "top":
            rect = rect.adjusted(-m, 0, m, -min(0, tl))
        elif self.orientation == "bottom":
            rect = rect.adjusted(-m, min(0, tl), m, 0)

        return rect

    def drawPicture(self, p, axisSpec, tickSpecs, textSpecs):
        # Tilts the x-axis labels
        super().drawPicture(p, axisSpec, tickSpecs, [])

        # Set label position, depending on tilt angle
        x_offset = -26
        y_offset = -3

        for rect, flags, text in textSpecs:
            p.save()
            p.setClipping(False)

            p.translate(rect.center())
            p.rotate(self.label_angle)
            p.translate(-rect.center())

            p.translate(x_offset, y_offset)

            p.drawText(rect, flags, text)
            p.restore()


class CustomPlotItem(pg.PlotItem):
    """Makes autorange appear bottom right not left"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def resizeEvent(self, ev):
        if self.autoBtn is None:
            return
        btnRect = self.mapRectFromItem(self.autoBtn, self.autoBtn.boundingRect())
        y = self.size().height() - btnRect.height()
        x = self.size().width() - btnRect.width()
        self.autoBtn.setPos(x, y)


def get_color_from_name(color_name, opacity=255):
    """Color name to RGB"""
    color = QColor(color_name)
    if color.isValid():
        return (color.red(), color.green(), color.blue(), opacity)
    else:
        return (0, 0, 0, opacity)


def get_shape_symbol(shape_name):
    """Shape name to identifier"""
    if shape_name == "Circle":
        return "o"
    elif shape_name == "Square":
        return "s"
    elif shape_name == "Triangle":
        return "t"
    else:
        return "o"


class MainWindow(QMainWindow):
    """

    Initialization and Database Interaction

    """

    def __init__(self):
        super().__init__()

        # Sets the style
        app.setStyle("Fusion")

        # Initialize database
        self.initialize_database()
        # Window title
        self.setWindowTitle("Food Tracker")
        # Window size
        self.setGeometry(100, 100, 1200, 600)
        # Window icon
        self.setWindowIcon(QIcon("icon.ico"))

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QHBoxLayout(main_widget)

        left_layout = QVBoxLayout()

        # Create table
        self.create_table(left_layout)

        # Create buttons and such
        self.create_input_section(left_layout)

        # Create graph
        graph_widget = self.create_graph()
        self.main_layout.addLayout(left_layout)
        # Graph resizing
        self.main_layout.addWidget(graph_widget, stretch=1)

        # Load settings from database
        self.load_settings()

        # Set current date
        self.selected_date = QDate.currentDate()

        self.new_food_layout = None
        self.update_table()

        # Highlight selected date
        self.highlight_selected_date()

    def initialize_database(self):
        """Initialized the database"""
        # Checks for database
        db_exists = os.path.exists("database.db")

        # Connect to SQLite database
        self.conn = sqlite3.connect("database.db")
        self.cursor = self.conn.cursor()

        # Sets up database if it doesn't exist yet
        if not db_exists:
            self.cursor.execute(
                """CREATE TABLE IF NOT EXISTS settings (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    line1_color TEXT,
                                    line2_color TEXT,
                                    font_size TEXT,
                                    font_type TEXT,
                                    weight_color TEXT,
                                    weight_shape TEXT,
                                    weight_opacity REAL,
                                    weight_size REAL,
                                    calories_in_color TEXT,
                                    calories_in_shape TEXT,
                                    calories_in_opacity REAL,
                                    calories_in_size REAL,
                                    calories_out_color TEXT,
                                    calories_out_shape TEXT,
                                    calories_out_opacity REAL,
                                    calories_out_size REAL)"""
            )

            self.cursor.execute(
                """CREATE TABLE IF NOT EXISTS basic_food (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    food_name TEXT,
                                    calories_per_100g REAL,
                                    protein_per_100g REAL)"""
            )

            self.cursor.execute(
                """CREATE TABLE IF NOT EXISTS composite_food (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    food_name TEXT,
                                    ingredients TEXT,  -- Stores the list of ingredients in format (name, amount)
                                    calories_per_100g REAL,
                                    protein_per_100g REAL)"""
            )

            self.cursor.execute(
                """CREATE TABLE IF NOT EXISTS daily_data (
                                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        date TEXT UNIQUE,
                                        weight REAL,
                                        food_consumed TEXT,  -- This stores a list of foods and amounts in format (name, amount)
                                        exercises TEXT)"""
            )
            self.cursor.execute(
                """INSERT INTO settings (line1_color, line2_color, font_size, font_type,
                                                         weight_color, weight_shape, weight_opacity, weight_size,
                                                         calories_in_color, calories_in_shape, calories_in_opacity, calories_in_size,
                                                         calories_out_color, calories_out_shape, calories_out_opacity, calories_out_size)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                # Default settings
                (
                    "blue",
                    "red",
                    "Medium",
                    "Arial",
                    "blue",
                    "Circle",
                    100,
                    10,
                    "green",
                    "Square",
                    100,
                    10,
                    "red",
                    "Triangle",
                    100,
                    10,
                ),
            )
            self.conn.commit()

    def load_settings(self):
        """Load settings from the database"""
        self.cursor.execute(
            """SELECT line1_color, line2_color, font_size, font_type,
                                      weight_color, weight_shape, weight_opacity, weight_size,
                                      calories_in_color, calories_in_shape, calories_in_opacity, calories_in_size,
                                      calories_out_color, calories_out_shape, calories_out_opacity, calories_out_size
                               FROM settings LIMIT 1"""
        )
        settings = self.cursor.fetchone()

        if settings:
            (
                self.line1_color,
                self.line2_color,
                self.font_size,
                self.font_type,
                self.weight_color,
                self.weight_shape,
                self.weight_opacity,
                self.weight_size,
                self.calories_in_color,
                self.calories_in_shape,
                self.calories_in_opacity,
                self.calories_in_size,
                self.calories_out_color,
                self.calories_out_shape,
                self.calories_out_opacity,
                self.calories_out_size,
            ) = settings

            # Apply settings
            self.apply_font_to_widgets(self.font_type, self.font_size)

        # Fallback settings
        else:
            self.line1_color = "blue"
            self.line2_color = "red"
            self.font_size = "Medium"
            self.font_type = "Arial"
            self.weight_color = "blue"
            self.weight_shape = "Circle"
            self.weight_opacity = 100
            self.weight_size = 10
            self.calories_in_color = "green"
            self.calories_in_shape = "Square"
            self.calories_in_opacity = 100
            self.calories_in_size = 10
            self.calories_out_color = "red"
            self.calories_out_shape = "Triangle"
            self.calories_out_opacity = 100
            self.calories_out_size = 10

    def save_settings(self, line1_color=None, line2_color=None, font_size=None, font_type=None):
        """Save settings to the database"""
        # Old needs to be removed later
        if line1_color:
            self.line1_color = line1_color
        if line2_color:
            self.line2_color = line2_color
        if font_size:
            self.font_size = font_size
        if font_type:
            self.font_type = font_type

        # Proper settings
        self.cursor.execute(
            """UPDATE settings SET
                                line1_color = ?, line2_color = ?, font_size = ?, font_type = ?,
                                weight_color = ?, weight_shape = ?, weight_opacity = ?, weight_size = ?,
                                calories_in_color = ?, calories_in_shape = ?, calories_in_opacity = ?, calories_in_size = ?,
                                calories_out_color = ?, calories_out_shape = ?, calories_out_opacity = ?, calories_out_size = ?""",
            (
                self.line1_color,
                self.line2_color,
                self.font_size,
                self.font_type,
                self.weight_color,
                self.weight_shape,
                self.weight_opacity,
                self.weight_size,
                self.calories_in_color,
                self.calories_in_shape,
                self.calories_in_opacity,
                self.calories_in_size,
                self.calories_out_color,
                self.calories_out_shape,
                self.calories_out_opacity,
                self.calories_out_size,
            ),
        )
        self.conn.commit()

    def save_daily_data(self, date, weight, food_consumed, exercises):
        """Saves user inputted data to the database"""
        food_str = ";".join([f"{name},{amount}" for name, amount in food_consumed])
        exercise_str = ";".join([f"{name},{calories}" for name, calories in exercises])
        self.cursor.execute(
            """INSERT OR REPLACE INTO daily_data (date, weight, food_consumed, exercises)
                               VALUES (?, ?, ?, ?)""",
            (date, weight, food_str, exercise_str),
        )
        self.conn.commit()

    def load_daily_data(self, date):
        """Loads previous user inputs from the database"""
        self.cursor.execute(
            "SELECT weight, food_consumed, exercises FROM daily_data WHERE date = ?", (date,)
        )
        data = self.cursor.fetchone()

        if data:
            weight, food_consumed, exercises = data

            # Food data (calories in)
            food_list = []
            if food_consumed:
                try:
                    food_list = [tuple(item.split(",")) for item in food_consumed.split(";")]
                except ValueError:
                    # In case of errors
                    pass

            # Exercise data (calories out)
            exercise_list = []
            if exercises:
                try:
                    exercise_list = [tuple(item.split(",")) for item in exercises.split(";")]
                except ValueError:
                    # In case of errors
                    pass

            return weight, food_list, exercise_list

        return None, [], []

    def update_table_from_database(self, data):
        """Updates the visible table with the entries from the database"""
        # Sets the rows based on the data
        self.table.setRowCount(len(data))
        for row_idx, row_data in enumerate(data):
            for col_idx, value in enumerate(row_data):
                # Sets the relevant column
                item = QTableWidgetItem(str(value))
                # Center-align the text
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Add the item to the table
                self.table.setItem(row_idx, col_idx, item)

        # Prevent clipping
        self.table.resizeRowsToContents()
        # Prevent clipping
        self.table.resizeColumnsToContents()
        # Enables scroll bar
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # Disables scroll bar
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    # Closes the connection with the database
    def closeEvent(self, event):
        self.conn.close()
        event.accept()

    """
    
    UI Management
    
    """

    def create_table(self, layout):
        """Creates the table"""
        # Seven columns, dynamic rows
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            [
                "Date",
                "Weight (kg)",
                "Calories In",
                "Calories Out",
                "Protein (g)",
                "\u0394 Prior (kg)",  # Delta symbol
                "\u0394 Goal (kg)",
            ]
        )

        font = self.table.horizontalHeader().font()
        # Bold header
        font.setBold(True)
        self.table.horizontalHeader().setFont(font)

        # Alternate row colours
        self.table.setAlternatingRowColors(True)

        # Prevents odd empty space in table
        self.table.horizontalHeader().setStretchLastSection(False)
        # Prevents clipping
        self.table.resizeColumnsToContents()

        # Diables scroll bar
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Enables scroll bar
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Prevents gaps
        self.table.setSizeAdjustPolicy(QTableWidget.SizeAdjustPolicy.AdjustToContents)

        # Prevents editing
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # Prevents gaps
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.table)

    def create_input_section(self, layout):
        """Creates the buttons and input fields"""
        # Weight input
        field_label_1 = QLabel("Weight")
        layout.addWidget(field_label_1)
        input_layout_1 = QHBoxLayout()
        self.input_field_1 = QLineEdit()
        self.input_field_1.setFixedWidth(InputWidth)
        btn_1 = QPushButton("Add")
        btn_1.setFixedWidth(ButtonWidth)
        spacer = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # Settings button
        btn_2 = QPushButton("Settings")
        btn_2.setFixedWidth(ButtonWidth)
        # Connect to popup
        btn_2.clicked.connect(self.show_settings_popup)
        input_layout_1.addWidget(self.input_field_1)
        input_layout_1.addWidget(btn_1)
        input_layout_1.addSpacerItem(spacer)
        input_layout_1.addWidget(btn_2)
        layout.addLayout(input_layout_1)
        btn_1.clicked.connect(self.save_weight)

        # Exercise input
        label_layout = QHBoxLayout()
        search_field_1_label = QLabel("Exercise")
        search_field_2_label = QLabel("Calories")
        spacer_middle = QSpacerItem(
            20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        label_layout.addWidget(search_field_1_label)
        label_layout.addSpacerItem(spacer_middle)
        label_layout.addWidget(search_field_2_label)
        search_field_2_label.setFixedWidth(ButtonWidth + InputWidth + 5)
        layout.addLayout(label_layout)
        input_layout_2 = QHBoxLayout()
        self.dropdown_1 = QComboBox()
        self.dropdown_1.setEditable(True)
        # Populate with exercises
        self.populate_dropdown(self.dropdown_1, "exercise")
        self.dropdown_1.setCurrentIndex(-1)
        self.input_field_2 = QLineEdit()
        self.input_field_2.setFixedWidth(InputWidth)
        btn_3 = QPushButton("Add")
        btn_3.setFixedWidth(ButtonWidth)
        btn_3.clicked.connect(self.save_exercise)
        input_layout_2.addWidget(self.dropdown_1)
        input_layout_2.addWidget(self.input_field_2)
        input_layout_2.addWidget(btn_3)
        layout.addLayout(input_layout_2)

        # Food input
        label_layout = QHBoxLayout()
        search_field_3_label = QLabel("Food")
        search_field_4_label = QLabel("Quantity (g)")
        label_layout.addWidget(search_field_3_label)
        label_layout.addSpacerItem(spacer_middle)
        label_layout.addWidget(search_field_4_label)
        search_field_4_label.setFixedWidth(ButtonWidth + InputWidth + 5)
        layout.addLayout(label_layout)
        input_layout_3 = QHBoxLayout()
        self.dropdown_2 = QComboBox()
        self.dropdown_2.setEditable(True)
        self.populate_dropdown(self.dropdown_2, "food")
        self.dropdown_2.setCurrentIndex(-1)
        self.input_field_3 = QLineEdit()
        self.input_field_3.setFixedWidth(InputWidth)
        btn_4 = QPushButton("Add")
        btn_4.setFixedWidth(ButtonWidth)
        btn_4.clicked.connect(self.save_food)
        input_layout_3.addWidget(self.dropdown_2)
        input_layout_3.addWidget(self.input_field_3)
        input_layout_3.addWidget(btn_4)
        layout.addLayout(input_layout_3)

        # Grams from Calories Calculator
        label_layout = QHBoxLayout()
        label_layout.addSpacerItem(spacer_middle)
        field_label_5 = QLabel("Calories")
        field_label_5.setFixedWidth(ButtonWidth + InputWidth + 5)
        label_layout.addWidget(field_label_5)
        layout.addLayout(label_layout)
        input_layout_4 = QHBoxLayout()
        spacer_left = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.input_field_4 = QLineEdit()
        self.input_field_4.setFixedWidth(InputWidth)
        # Add new food button
        btn_9 = QPushButton("New Food")
        btn_9.setFixedWidth(ButtonWidth)
        # Connect to popup
        btn_9.clicked.connect(self.show_new_food_popup)
        btn_5 = QPushButton("Calculate")
        btn_5.setFixedWidth(ButtonWidth)
        btn_5.clicked.connect(self.calculate_food_quantity)
        input_layout_4.addWidget(btn_9)
        # Add a spacer to the left
        input_layout_4.addSpacerItem(spacer_left)
        input_layout_4.addWidget(self.input_field_4)
        input_layout_4.addWidget(btn_5)
        layout.addLayout(input_layout_4)

        # Date selectors
        btn_layout = QHBoxLayout()
        btn_6 = QPushButton("Previous Day")
        btn_7 = QPushButton("Date")
        btn_8 = QPushButton("Next Day")
        btn_layout.addWidget(btn_6)
        btn_layout.addWidget(btn_7)
        # Connect to popup
        btn_7.clicked.connect(self.show_date_popup)
        btn_layout.addWidget(btn_8)
        layout.addLayout(btn_layout)
        btn_6.clicked.connect(self.move_to_previous_day)
        btn_8.clicked.connect(self.move_to_next_day)

    def show_settings_popup(self):
        """Creates the settings popup"""
        # QDialog for settings popup
        self.settings_dialog = QDialog(self)
        self.settings_dialog.setWindowTitle("Settings")

        self.settings_layout = QVBoxLayout()

        # Buttons for Edit Food, Edit Date, Graph, Font, and Cancel
        btn_edit_food = QPushButton("Edit Food")
        btn_edit_date = QPushButton("Edit Date")
        btn_graph = QPushButton("Graph")
        btn_font = QPushButton("Font")
        btn_cancel = QPushButton("Cancel")

        # Connect buttons to their respective methods
        btn_edit_food.clicked.connect(self.show_edit_food)
        btn_edit_date.clicked.connect(self.show_edit_date)
        btn_graph.clicked.connect(self.show_graph_settings)
        btn_font.clicked.connect(self.show_font_settings)
        btn_cancel.clicked.connect(self.settings_dialog.reject)

        # Add buttons to layout
        self.settings_layout.addWidget(btn_edit_food)
        self.settings_layout.addWidget(btn_edit_date)
        self.settings_layout.addWidget(btn_graph)
        self.settings_layout.addWidget(btn_font)
        self.settings_layout.addWidget(btn_cancel)

        self.settings_dialog.setLayout(self.settings_layout)
        self.settings_dialog.exec()

    # Clears the layout
    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())

    # Clears the layout
    def clear_settings_layout(self):
        while self.settings_layout.count():
            item = self.settings_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())

    def refresh_food_dropdowns(self):
        """Refresh all food dropdowns with updated data from the database"""
        # Clear the existing dropdown items
        self.dropdown_2.clear()

        # Fetch all the food items from the basic and composite food tables
        self.cursor.execute(
            "SELECT food_name FROM basic_food UNION SELECT food_name FROM composite_food"
        )
        foods = self.cursor.fetchall()

        # Add new food items to the dropdown
        for food in foods:
            self.dropdown_2.addItem(food[0])

    def populate_dropdown(self, dropdown, type):
        """Populate dropdown menu with food or exercise entries from the database"""
        # Clear existing items
        dropdown.clear()

        if type == "food":
            # Fetch all food items from both basic and composite food tables
            self.cursor.execute(
                "SELECT food_name FROM basic_food UNION SELECT food_name FROM composite_food"
            )
            foods = self.cursor.fetchall()
            for food in foods:
                dropdown.addItem(food[0])
        elif type == "exercise":
            # Predefined exercise options
            exercises = ["Cycling", "Swimming", "Jogging", "Climbing", "Weight Training"]
            for exercise in exercises:
                dropdown.addItem(exercise)

    def show_new_food_popup(self):
        """Popup to add new food options"""
        # QDialog for the new food popup
        self.new_food_dialog = QDialog(self)
        self.new_food_dialog.setWindowTitle("New Food Entry")

        # Create a main layout
        self.new_food_layout = QVBoxLayout()

        # Buttons for Basic and Composite
        self.show_initial_food_buttons()

        # Set the dialog layout
        self.new_food_dialog.setLayout(self.new_food_layout)
        self.new_food_dialog.exec()

    def show_initial_food_buttons(self):
        """The Basic and Composite food buttons"""
        # Clear existing layout
        self.clear_new_food_layout()

        # Buttons for Basic or Composite
        btn_basic = QPushButton("Basic")
        btn_composite = QPushButton("Composite")

        # Connect buttons to layout functions
        btn_basic.clicked.connect(self.show_basic_food_form)
        btn_composite.clicked.connect(self.show_composite_food_form)

        # Add buttons to the layout
        button_layout = QHBoxLayout()
        button_layout.addWidget(btn_basic)
        button_layout.addWidget(btn_composite)

        # Add button layout to the main layout
        self.new_food_layout.addLayout(button_layout)

    def clear_new_food_layout(self):
        """Clears the layout"""
        while self.new_food_layout.count():
            item = self.new_food_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())

    def show_font_settings(self):
        """Shows the fonts settings section"""
        # Clear the settings layout
        self.clear_settings_layout()

        # Dropdown menus
        self.dropdown_font_size = QComboBox()
        self.dropdown_font_type = QComboBox()

        # Populate
        font_sizes = ["Small", "Medium", "Large"]
        font_types = ["Arial", "Helvetica", "Times New Roman", "Courier"]

        self.dropdown_font_size.addItems(font_sizes)
        self.dropdown_font_type.addItems(font_types)

        # Buttons to save or cancel
        btn_save = QPushButton("Save")
        btn_cancel = QPushButton("Cancel")
        btn_save.clicked.connect(self.apply_font_settings)
        btn_cancel.clicked.connect(self.settings_dialog.reject)

        # Layout for Font settings
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Font Size:"))
        layout.addWidget(self.dropdown_font_size)
        layout.addWidget(QLabel("Font Type:"))
        layout.addWidget(self.dropdown_font_type)

        button_layout = QHBoxLayout()
        button_layout.addWidget(btn_save)
        button_layout.addWidget(btn_cancel)

        layout.addLayout(button_layout)

        self.settings_layout.addLayout(layout)
        self.settings_dialog.adjustSize()

    def apply_font_to_widgets(self, font_type, font_size):
        """Sets font size and type"""
        if font_size == "Small":
            point_size = 10
        elif font_size == "Medium":
            point_size = 14
        elif font_size == "Large":
            point_size = 18

        # Create the QFont object
        font = QFont(font_type, point_size)

        # Apply the font
        self.setFont(font)

    def apply_font_settings(self):
        """Applies and saves font settings"""
        font_type = self.dropdown_font_type.currentText()
        font_size = self.dropdown_font_size.currentText()
        self.apply_font_to_widgets(font_type, font_size)

        # Save the font settings to the database
        self.save_settings(font_size=font_size, font_type=font_type)
        self.settings_dialog.accept()

    def show_date_popup(self):
        """Select a date from a calendar"""
        # QDialog for the date popup
        date_dialog = QDialog(self)
        date_dialog.setWindowTitle("Select Date")

        # Layout for the popup
        layout = QVBoxLayout()

        # Calendar widget
        self.calendar = QCalendarWidget()
        # Set default date to today's date
        self.calendar.setSelectedDate(QDate.currentDate())

        layout.addWidget(self.calendar)

        # Buttons for Select and Cancel
        button_layout = QHBoxLayout()
        btn_select = QPushButton("Select")
        btn_cancel = QPushButton("Cancel")

        # Connect the buttons to
        btn_select.clicked.connect(lambda: self.select_date(date_dialog))
        btn_cancel.clicked.connect(date_dialog.reject)

        button_layout.addWidget(btn_select)
        button_layout.addWidget(btn_cancel)

        # Add to the layout
        layout.addLayout(button_layout)

        # Set the layout
        date_dialog.setLayout(layout)

        # Execute
        date_dialog.exec()

    def select_date(self, dialog):
        """Set the selected date from the calendar and highlight it in the table."""
        # Get the selected date
        self.selected_date = self.calendar.selectedDate()
        # Highlight the row in the table
        self.highlight_selected_date()
        # Close the dialog
        dialog.accept()

    def show_edit_food(self):
        """Edit food part of the settings menu"""
        # Clear the layout
        self.clear_settings_layout()

        # Dropdown for selecting the food to edit
        self.food_dropdown = QComboBox()
        self.food_dropdown.setEditable(True)

        # Populate the dropdown with all foods
        self.populate_dropdown(self.food_dropdown, "food")

        # Buttons to load the selected food or cancel
        btn_load = QPushButton("Edit")
        btn_cancel = QPushButton("Cancel")
        btn_load.clicked.connect(self.load_food_for_edit)
        btn_cancel.clicked.connect(self.settings_dialog.reject)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Select Food:"))
        layout.addWidget(self.food_dropdown)
        self.food_dropdown.setCurrentIndex(-1)

        button_layout = QHBoxLayout()
        button_layout.addWidget(btn_load)
        button_layout.addWidget(btn_cancel)

        layout.addLayout(button_layout)

        self.settings_layout.addLayout(layout)
        self.settings_dialog.adjustSize()

    def show_edit_date(self):
        """Edit date part of the settings menu"""
        # Clear the layout
        self.clear_settings_layout()

        # Selecting the date
        self.calendar = QCalendarWidget()
        self.calendar.setSelectedDate(QDate.currentDate())  # Default to current date

        # Buttons to load the data for the selected date or cancel
        btn_edit = QPushButton("Edit")
        btn_cancel = QPushButton("Cancel")
        btn_edit.clicked.connect(self.load_data_for_date)
        btn_cancel.clicked.connect(self.settings_dialog.reject)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.calendar)

        button_layout = QHBoxLayout()
        button_layout.addWidget(btn_edit)
        button_layout.addWidget(btn_cancel)

        layout.addLayout(button_layout)

        self.settings_layout.addLayout(layout)
        self.settings_dialog.adjustSize()

    def load_food_for_edit(self):
        """Loads the food from database to edit it"""
        selected_food = self.food_dropdown.currentText()

        # Do nothing if no food is selected
        if not selected_food:
            return

        # Check if the food is Basic or Composite
        self.cursor.execute(
            "SELECT calories_per_100g, protein_per_100g FROM basic_food WHERE food_name = ?",
            (selected_food,),
        )
        basic_food = self.cursor.fetchone()

        if basic_food:
            # If it's a Basic food, load the Basic food form
            self.show_basic_food_form(edit=True, food_data=basic_food, food_name=selected_food)
        else:
            # Check if it's Composite
            self.cursor.execute(
                "SELECT ingredients, calories_per_100g, protein_per_100g FROM composite_food WHERE food_name = ?",
                (selected_food,),
            )
            composite_food = self.cursor.fetchone()

            if composite_food:
                # If it's a Composite food, load the Composite food form
                self.show_composite_food_form(
                    edit=True, food_data=composite_food, food_name=selected_food
                )

    def load_data_for_date(self):
        """Loads the data for a selected date"""
        selected_date = self.calendar.selectedDate().toString(Qt.DateFormat.ISODate)

        # Fetch data from the database
        self.cursor.execute(
            "SELECT weight, food_consumed, exercises FROM daily_data WHERE date = ?",
            (selected_date,),
        )
        data = self.cursor.fetchone()

        if data:
            weight, food_consumed, exercises = data
        else:
            weight, food_consumed, exercises = None, "", ""

        # Pass the data on
        self.show_date_data_form(selected_date, weight, food_consumed, exercises)

    def show_date_data_form(self, date, weight=None, food_consumed="", exercises=""):
        """The form that allows editing all parts of a chosen date, weight, exercise, and food"""
        # Clear the layout
        self.clear_settings_layout()

        # Add a new layout
        self.date_data_layout = QVBoxLayout()

        # Weight input
        self.weight_input = QLineEdit()
        self.weight_input.setText(f"{weight}" if weight else "")
        weight_layout = QHBoxLayout()
        weight_layout.addWidget(QLabel("Weight:"))
        weight_layout.addWidget(self.weight_input)

        # Ensure weight is added first
        self.date_data_layout.addLayout(weight_layout)

        # Create sub-layouts for food and exercise
        self.food_layout = QVBoxLayout()
        self.exercise_layout = QVBoxLayout()

        # Section for food entries
        self.food_rows = []
        food_list = (
            [tuple(item.split(",")) for item in food_consumed.split(";")] if food_consumed else []
        )
        for food_name, amount in food_list:
            self.add_food_row(food_name, amount)

        # Section for exercise entries
        self.exercise_rows = []
        exercise_list = (
            [tuple(item.split(",")) for item in exercises.split(";")] if exercises else []
        )
        for exercise_name, calories in exercise_list:
            self.add_exercise_row(exercise_name, calories)

        # Add the food and exercise layouts to the main layout
        self.date_data_layout.addLayout(self.food_layout)
        self.date_data_layout.addLayout(self.exercise_layout)

        # Add buttons for adding new food/exercise below the current rows
        add_food_button = QPushButton("Add Food")
        add_food_button.clicked.connect(self.add_food_row)
        add_exercise_button = QPushButton("Add Exercise")
        add_exercise_button.clicked.connect(self.add_exercise_row)

        # Add the buttons at the bottom of the current entries
        self.date_data_layout.addWidget(add_food_button)
        self.date_data_layout.addWidget(add_exercise_button)

        # Add Save and Cancel buttons at the bottom
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(lambda: self.save_date_data(date))
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.settings_dialog.reject)

        button_layout = QHBoxLayout()
        button_layout.addWidget(btn_save)
        button_layout.addWidget(btn_cancel)

        # Ensure buttons layout is last
        self.date_data_layout.addLayout(button_layout)

        # Add the entire layout to the dialog
        self.settings_layout.addLayout(self.date_data_layout)

        # Adjust window size after adding the elements
        self.settings_dialog.adjustSize()

    def add_food_row(self, food_name="", amount=""):
        """Add a new row for a food entry"""
        row_layout = QHBoxLayout()

        food_dropdown = QComboBox()
        food_dropdown.setEditable(True)
        self.populate_dropdown(food_dropdown, "food")

        food_dropdown.setCurrentText(food_name if food_name else "")

        amount_input = QLineEdit()
        amount_input.setText(f"{amount}" if amount else "")

        row_layout.addWidget(food_dropdown)
        row_layout.addWidget(amount_input)

        self.food_rows.append((food_dropdown, amount_input))
        self.food_layout.addLayout(row_layout)

    def add_exercise_row(self, exercise_name="", calories=""):
        """Add a new row for an exercise entry"""
        row_layout = QHBoxLayout()

        exercise_dropdown = QComboBox()
        exercise_dropdown.setEditable(True)
        self.populate_dropdown(exercise_dropdown, "exercise")

        exercise_dropdown.setCurrentText(exercise_name if exercise_name else "")

        calories_input = QLineEdit()
        calories_input.setText(f"{calories}" if calories else "")

        row_layout.addWidget(exercise_dropdown)
        row_layout.addWidget(calories_input)

        self.exercise_rows.append((exercise_dropdown, calories_input))
        self.exercise_layout.addLayout(row_layout)

    def add_composite_ingredient(self):
        """Adds another row for an inredient for composite foods"""
        new_dropdown = QComboBox()
        new_dropdown.setEditable(True)

        new_input = QLineEdit()

        new_row = QHBoxLayout()
        new_row.addWidget(new_dropdown)
        new_row.addWidget(new_input)

        # Add just above Additional Ingredient button
        self.composite_layout.insertLayout(self.composite_layout.count() - 1, new_row)
        # Adjust size dynamically after adding rows
        self.new_food_dialog.adjustSize()

    """Data Saving"""

    def save_weight(self):
        """Saves the weight to the database"""
        weight = self.input_field_1.text()
        if weight:
            weight = float(weight)
            # Load existing data for the date
            self.cursor.execute(
                "SELECT food_consumed, exercises FROM daily_data WHERE date = ?",
                (self.selected_date.toString(Qt.DateFormat.ISODate),),
            )
            existing_data = self.cursor.fetchone()

            if existing_data:
                food_consumed, exercises = existing_data
            else:
                # Initialize if no data exists
                food_consumed, exercises = "", ""

            # Update the database with the new weight
            self.cursor.execute(
                "INSERT OR REPLACE INTO daily_data (date, weight, food_consumed, exercises) VALUES (?, ?, ?, ?)",
                (
                    self.selected_date.toString(Qt.DateFormat.ISODate),
                    weight,
                    food_consumed,
                    exercises,
                ),
            )
            self.conn.commit()
            self.update_table()
            self.update_graph()

    def save_food(self):
        """Saves the food to the database"""
        food = self.dropdown_2.currentText()
        quantity = self.input_field_3.text()
        if food and quantity:
            quantity = float(quantity)
            # Load existing data for the date
            self.cursor.execute(
                "SELECT weight, exercises, food_consumed FROM daily_data WHERE date = ?",
                (self.selected_date.toString(Qt.DateFormat.ISODate),),
            )
            existing_data = self.cursor.fetchone()

            if existing_data:
                weight, exercises, food_consumed = existing_data
            else:
                # Initialize if no data exists
                weight, exercises, food_consumed = None, "", ""

            food_str = f"{food},{quantity}"
            if food_consumed:
                # Append to existing food entries
                new_food = food_consumed + f";{food_str}"
            else:
                new_food = food_str

            # Update the database with the new food data
            self.cursor.execute(
                "INSERT OR REPLACE INTO daily_data (date, weight, food_consumed, exercises) VALUES (?, ?, ?, ?)",
                (self.selected_date.toString(Qt.DateFormat.ISODate), weight, new_food, exercises),
            )
            self.conn.commit()
            self.update_table()
            self.update_graph()

    def save_exercise(self):
        """Saves the exercise to the database"""
        exercise = self.dropdown_1.currentText()
        calories = self.input_field_2.text()
        if exercise and calories:
            calories = float(calories)
            # Load existing data for the date
            self.cursor.execute(
                "SELECT weight, food_consumed, exercises FROM daily_data WHERE date = ?",
                (self.selected_date.toString(Qt.DateFormat.ISODate),),
            )
            existing_data = self.cursor.fetchone()

            if existing_data:
                weight, food_consumed, exercises = existing_data
            else:
                # Initialize if no data exists
                weight, food_consumed, exercises = None, "", ""

            exercise_str = f"{exercise},{calories}"
            if exercises:
                # Append to existing exercises
                new_exercises = exercises + f";{exercise_str}"
            else:
                new_exercises = exercise_str

            # Update the database with the new exercise data
            self.cursor.execute(
                "INSERT OR REPLACE INTO daily_data (date, weight, food_consumed, exercises) VALUES (?, ?, ?, ?)",
                (
                    self.selected_date.toString(Qt.DateFormat.ISODate),
                    weight,
                    food_consumed,
                    new_exercises,
                ),
            )
            self.conn.commit()
            self.update_table()
            self.update_graph()

    def calculate_food_quantity(self):
        """Calculate grams from calories"""
        food = self.dropdown_2.currentText()
        calories = self.input_field_4.text()
        if food and calories:
            calories = float(calories)
            # Load the food's calorie data
            self.cursor.execute(
                "SELECT calories_per_100g FROM basic_food WHERE food_name = ? UNION SELECT calories_per_100g FROM composite_food WHERE food_name = ?",
                (food, food),
            )
            food_data = self.cursor.fetchone()
            if food_data:
                calories_per_100g = food_data[0]
                if calories_per_100g > 0:
                    quantity = (calories / calories_per_100g) * 100
                    # Display the calculated value in the food input field
                    self.input_field_3.setText(f"{quantity:.2f}")

    def save_basic_food(self):
        """Saves a Basic food to the database"""
        # Get the values from the input fields
        food_name = self.input_1.text().strip()
        calories = self.input_2.text().strip()
        protein = self.input_3.text().strip()

        # Check inputs are not empty
        if not food_name or not calories or not protein:
            # Do nothing if any field is empty
            return

        # Insert the basic food into the database
        self.cursor.execute(
            """INSERT INTO basic_food (food_name, calories_per_100g, protein_per_100g)
                               VALUES (?, ?, ?)""",
            (food_name, float(calories), float(protein)),
        )
        self.conn.commit()

        # Refresh dropdowns to show the newly added food
        self.refresh_food_dropdowns()

        # Close the dialog
        self.new_food_dialog.accept()

    def update_basic_food(self):
        """Updates an edited Basic food in the database"""
        new_food_name = self.input_1.text().strip()
        calories = self.input_2.text().strip()
        protein = self.input_3.text().strip()
        old_food_name = self.food_dropdown.currentText().strip()

        if new_food_name and calories and protein:
            # Check if the new food name already exists
            self.cursor.execute(
                "SELECT food_name FROM basic_food WHERE food_name = ?", (new_food_name,)
            )
            existing_food = self.cursor.fetchone()

            if existing_food is None or new_food_name == old_food_name:
                # If the new name doesn't exist, update the record
                self.cursor.execute(
                    """UPDATE basic_food
                                       SET food_name = ?, calories_per_100g = ?, protein_per_100g = ?
                                       WHERE food_name = ?""",
                    (new_food_name, float(calories), float(protein), old_food_name),
                )
                self.conn.commit()

                # Refresh dropdowns after updating the food
                self.refresh_food_dropdowns()

                # Close the dialog
                self.new_food_dialog.accept()
            else:
                # Show error message
                print("A food with this name already exists.")

    def save_composite_food(self):
        """Saves a Composite food to the database"""
        composite_name = self.input_1.text().strip()
        if not composite_name:
            # Do nothing if name is empty
            return

        ingredients = []
        total_calories = 0
        total_protein = 0
        total_weight = 0

        # Loop through each ingredient row and collect data
        for dropdown, quantity_input in self.composite_ingredient_rows:
            ingredient_name = dropdown.currentText().strip()
            quantity = quantity_input.text().strip()

            if ingredient_name and quantity:
                # Fetch the calories and protein of the ingredient from the database
                self.cursor.execute(
                    """SELECT calories_per_100g, protein_per_100g
                                       FROM basic_food WHERE food_name = ?
                                       UNION SELECT calories_per_100g, protein_per_100g
                                       FROM composite_food WHERE food_name = ?""",
                    (ingredient_name, ingredient_name),
                )
                food_data = self.cursor.fetchone()

                if food_data:
                    calories_per_100g, protein_per_100g = food_data
                    ingredient_quantity = float(quantity)

                    total_calories += (calories_per_100g * ingredient_quantity) / 100
                    total_protein += (protein_per_100g * ingredient_quantity) / 100
                    total_weight += ingredient_quantity

                    ingredients.append((ingredient_name, ingredient_quantity))

        if total_weight > 0:
            # Calculate calories and protein per 100g of the composite food
            composite_calories_per_100g = (total_calories / total_weight) * 100
            composite_protein_per_100g = (total_protein / total_weight) * 100

            # Save the composite food to the database
            ingredients_str = ";".join([f"{name},{amount}" for name, amount in ingredients])
            self.cursor.execute(
                """INSERT INTO composite_food (food_name, ingredients, calories_per_100g, protein_per_100g)
                                   VALUES (?, ?, ?, ?)""",
                (
                    composite_name,
                    ingredients_str,
                    composite_calories_per_100g,
                    composite_protein_per_100g,
                ),
            )
            self.conn.commit()

        # Refresh dropdowns to show the newly added food
        self.refresh_food_dropdowns()

        # Close the dialog
        self.new_food_dialog.accept()

    def update_composite_food(self):
        """Updates an edited Composite food to the database"""
        new_composite_name = self.input_1.text().strip()
        old_composite_name = self.food_dropdown.currentText().strip()
        ingredients = []
        total_calories = 0
        total_protein = 0
        total_weight = 0

        # Loop through each ingredient row and collect data
        for dropdown, quantity_input in self.composite_ingredient_rows:
            ingredient_name = dropdown.currentText().strip()
            quantity = quantity_input.text().strip()

            if ingredient_name and quantity:
                self.cursor.execute(
                    """SELECT calories_per_100g, protein_per_100g
                                       FROM basic_food WHERE food_name = ?
                                       UNION SELECT calories_per_100g, protein_per_100g
                                       FROM composite_food WHERE food_name = ?""",
                    (ingredient_name, ingredient_name),
                )
                food_data = self.cursor.fetchone()

                if food_data:
                    calories_per_100g, protein_per_100g = food_data
                    ingredient_quantity = float(quantity)

                    total_calories += (calories_per_100g * ingredient_quantity) / 100
                    total_protein += (protein_per_100g * ingredient_quantity) / 100
                    total_weight += ingredient_quantity

                    ingredients.append((ingredient_name, ingredient_quantity))

        if total_weight > 0:
            composite_calories_per_100g = (total_calories / total_weight) * 100
            composite_protein_per_100g = (total_protein / total_weight) * 100

            ingredients_str = ";".join([f"{name},{amount}" for name, amount in ingredients])

            # Check if the new name already exists
            self.cursor.execute(
                "SELECT food_name FROM composite_food WHERE food_name = ?", (new_composite_name,)
            )
            existing_food = self.cursor.fetchone()

            if existing_food is None or new_composite_name == old_composite_name:
                # Update the composite food in the database
                self.cursor.execute(
                    """UPDATE composite_food
                                       SET food_name = ?, ingredients = ?, calories_per_100g = ?, protein_per_100g = ?
                                       WHERE food_name = ?""",
                    (
                        new_composite_name,
                        ingredients_str,
                        composite_calories_per_100g,
                        composite_protein_per_100g,
                        old_composite_name,
                    ),
                )
                self.conn.commit()

                # Refresh dropdowns to show the newly updated food
                self.refresh_food_dropdowns()

                # Close the dialog
                self.new_food_dialog.accept()
            else:
                # Show error messave
                print("A composite food with this name already exists.")

    def save_date_data(self, date):
        """Save or update the date's data in the database"""

        # Get the weight input
        weight = self.weight_input.text()
        # Remove from DB if empty
        weight = float(weight) if weight else None

        # Collect food data
        food_entries = []
        for food_dropdown, amount_input in self.food_rows:
            food_name = food_dropdown.currentText()
            amount = amount_input.text()
            if food_name and amount:
                food_entries.append((food_name, amount))

        # Collect exercise data
        exercise_entries = []
        for exercise_dropdown, calories_input in self.exercise_rows:
            exercise_name = exercise_dropdown.currentText()
            calories = calories_input.text()
            if exercise_name and calories:
                exercise_entries.append((exercise_name, calories))

        # Save the data to the database
        self.save_daily_data(date, weight, food_entries, exercise_entries)

        # Update table and graph
        self.update_table()
        self.update_graph()

        # Close the dialog
        self.settings_dialog.accept()

    """
    
    Navigation and Data Handling
    
    """

    def highlight_selected_date(self):
        """Highlight the row in the table corresponding to the selected date."""
        # Date: (ISO format: YYYY-MM-DD)
        selected_date_str = self.selected_date.toString(Qt.DateFormat.ISODate)

        # Search through the table rows to find a matching date
        for row in range(self.table.rowCount()):
            # The date is in the first column
            date_item = self.table.item(row, 0)
            if date_item and date_item.text() == selected_date_str:
                # Select the matching row
                self.table.selectRow(row)
                return
        # If no matching date is found, clear
        self.table.clearSelection()

    def move_to_previous_day(self):
        """Move the selected date back by 1 day."""
        self.selected_date = self.selected_date.addDays(-1)
        self.highlight_selected_date()

    def move_to_next_day(self):
        """Move the selected date forward by 1 day."""
        self.selected_date = self.selected_date.addDays(1)
        self.highlight_selected_date()

    """
    
    Graph Management
    
    """

    def create_graph(self):
        """Creates the graph"""
        # Create the main plot widget
        self.graph_widget = pg.PlotWidget(plotItem=CustomPlotItem())

        # Create a custom x-axis
        custom_axis = CustomAxisItem(orientation="bottom")  # Custom x-axis with rotation
        self.graph_widget.plotItem.setAxisItems({"bottom": custom_axis})

        # Set the background colour
        fusion_grey = QColor(73, 73, 73)
        fusion_grey_dark = QColor(53, 53, 53)
        self.graph_widget.setBackground(fusion_grey_dark)
        self.graph_widget.getPlotItem().getViewBox().setBackgroundColor(fusion_grey)

        # Customize axis colors
        axis_pen = pg.mkPen(color="w")
        self.graph_widget.getAxis("left").setPen(axis_pen)
        self.graph_widget.getAxis("bottom").setPen(axis_pen)
        self.graph_widget.getAxis("right").setPen(axis_pen)

        # Set the color of axis labels
        self.graph_widget.getAxis("left").setTextPen(axis_pen)
        self.graph_widget.getAxis("bottom").setTextPen(axis_pen)
        self.graph_widget.getAxis("right").setTextPen(axis_pen)

        # Set a fixed height for the bottom axis
        custom_axis.setHeight(58)

        # Set the labels for axes
        self.graph_widget.plotItem.setLabel("left", "Weight (kg)")

        # Add the right axis for calories
        self.graph_widget.plotItem.showAxis("right")
        self.graph_widget.getAxis("right").setLabel("Calories (kcal)")

        # Show grid only on the left y-axis and bottom x-axis
        self.graph_widget.showGrid(x=False, y=False, alpha=0.15)

        # Disable the right y-axis grid explicitly
        right_axis = self.graph_widget.plotItem.getAxis("right")
        right_axis.setGrid(0)

        # Create the legend and add it to the top of the graph
        self.legend = pg.LegendItem()
        self.legend.setParentItem(self.graph_widget.plotItem)
        self.legend.setColumnCount(3)
        self.legend.anchor(itemPos=(0.5, 0), parentPos=(0.5, 0), offset=(0, 0))

        return self.graph_widget

    def apply_graph_color_settings(self):
        """Have the graph relfect selected settings"""
        # Get graph settings from the dropdowns and inputs
        self.weight_color = self.weight_color_dropdown.currentText()
        self.weight_shape = self.weight_shape_dropdown.currentText()
        self.weight_opacity = float(self.weight_opacity_input.text())
        self.weight_size = float(self.weight_size_input.text())

        self.calories_in_color = self.calories_in_color_dropdown.currentText()
        self.calories_in_shape = self.calories_in_shape_dropdown.currentText()
        self.calories_in_opacity = float(self.calories_in_opacity_input.text())
        self.calories_in_size = float(self.calories_in_size_input.text())

        self.calories_out_color = self.calories_out_color_dropdown.currentText()
        self.calories_out_shape = self.calories_out_shape_dropdown.currentText()
        self.calories_out_opacity = float(self.calories_out_opacity_input.text())
        self.calories_out_size = float(self.calories_out_size_input.text())

        # Save the updated settings
        self.save_settings()

        # Update the graph
        self.update_graph()

        # Close the dialog
        self.settings_dialog.accept()

    def sync_right_y_axis(self):
        """Manually synchronize the right y-axis with the left y-axis but display actual calorie values."""
        # Get the left y-axis range
        left_range = self.graph_widget.plotItem.vb.viewRange()[1]
        # Upper bound of the weight range
        max_weight = left_range[1]

        # Check if max_calories and max_weight are greater than 0
        if self.max_calories > 0 and max_weight > 0:
            # Calculate the calorie range based on the normalization factor (a kg = b cal)
            normalization_factor = self.max_weight / self.max_calories

            # Update the ticks and labels for the right axis
            self.graph_widget.plotItem.getAxis("right").setTicks(
                [list(self.generate_right_axis_ticks(left_range, normalization_factor))]
            )

    def generate_right_axis_ticks(self, left_range, normalization_factor):
        """Generate ticks for the right y-axis based on the left y-axis range and normalization factor."""
        left_min, left_max = left_range
        right_min = left_min / normalization_factor
        right_max = left_max / normalization_factor

        # Find the closest multiple of 100 to the min and max values for nice tick marks
        right_min = (int(right_min) // 100) * 100
        right_max = (int(right_max) // 100 + 1) * 100

        # Generate tick labels for the right axis
        right_ticks = []
        for right_value in range(int(right_min), int(right_max) + 1, 100):
            left_value = right_value * normalization_factor
            right_ticks.append((left_value, f"{right_value}"))

        return right_ticks

    def update_graph(self):
        """Updates the graph to reflect any changes in data or settings"""
        # Clear existing items in the graph
        for item in self.graph_widget.listDataItems():
            self.graph_widget.removeItem(item)

        # Clear the previous legend entries
        self.legend.clear()

        # Fetch data from the table
        dates = []
        weights = []
        calories_in = []
        calories_out = []

        # Loop through the table to extract data
        for row in range(self.table.rowCount()):
            # Date
            date_item = self.table.item(row, 0)
            # Weight
            weight_item = self.table.item(row, 1)
            # Calories In
            calories_in_item = self.table.item(row, 2)
            # Calories Out
            calories_out_item = self.table.item(row, 3)

            # Append data to lists
            if date_item and weight_item and calories_in_item and calories_out_item:
                dates.append(date_item.text())
                weights.append(float(weight_item.text()) if weight_item.text() != "N/A" else None)
                calories_in.append(
                    float(calories_in_item.text()) if calories_in_item.text() != "N/A" else 0
                )
                calories_out.append(
                    float(calories_out_item.text()) if calories_out_item.text() != "N/A" else 0
                )

        # Reverse data
        dates.reverse()
        weights.reverse()
        calories_in.reverse()
        calories_out.reverse()

        # Create indices for the x-axis
        date_indices = list(range(len(dates)))

        # Find the maximum weight and calorie value for normalization
        self.max_weight = max([w for w in weights if w is not None]) if weights else 0
        self.max_calories = (
            max(max(calories_in), max(calories_out)) if calories_in and calories_out else 0
        )

        # Normalize calories based on max weight (a kg = b cal)
        normalization_factor = self.max_weight / self.max_calories if self.max_calories > 0 else 1

        # Normalize calories_in and calories_out for plotting
        normalized_calories_in = [cal * normalization_factor for cal in calories_in]
        normalized_calories_out = [cal * normalization_factor for cal in calories_out]

        # Convert color names
        weight_color = get_color_from_name(self.weight_color, int(self.weight_opacity * 2.55))
        calories_in_color = get_color_from_name(
            self.calories_in_color, int(self.calories_in_opacity * 2.55)
        )
        calories_out_color = get_color_from_name(
            self.calories_out_color, int(self.calories_out_opacity * 2.55)
        )

        # Plot the weight data on the left y-axis
        weight_shape_symbol = get_shape_symbol(self.weight_shape)
        calories_in_shape_symbol = get_shape_symbol(self.calories_in_shape)
        calories_out_shape_symbol = get_shape_symbol(self.calories_out_shape)

        # Plot normalized calories in/out on the right y-axis
        calories_out_scatter = pg.ScatterPlotItem(
            size=self.calories_out_size,
            pen=pg.mkPen(color=calories_out_color),
            brush=pg.mkBrush(calories_out_color),
            symbol=calories_out_shape_symbol,
        )
        calories_in_scatter = pg.ScatterPlotItem(
            size=self.calories_in_size,
            pen=pg.mkPen(color=calories_in_color),
            brush=pg.mkBrush(calories_in_color),
            symbol=calories_in_shape_symbol,
        )

        # Add the calorie scatter plots first
        calories_out_scatter.setData(date_indices, normalized_calories_out)
        self.graph_widget.addItem(calories_out_scatter)

        calories_in_scatter.setData(date_indices, normalized_calories_in)
        self.graph_widget.addItem(calories_in_scatter)

        # Plot the weight data
        weight_scatter = pg.ScatterPlotItem(
            size=self.weight_size,
            pen=pg.mkPen(color=weight_color),
            brush=pg.mkBrush(weight_color),
            symbol=weight_shape_symbol,
        )
        weight_scatter.setData(date_indices, weights)
        self.graph_widget.addItem(weight_scatter)

        # Add entries to the legend
        self.legend.addItem(weight_scatter, "Weight")
        self.legend.addItem(calories_in_scatter, "Calories In")
        self.legend.addItem(calories_out_scatter, "Calories Out")

        # Update the graph widget and force repaint
        self.graph_widget.getViewBox().update()
        self.graph_widget.repaint()

        # Set x-axis labels and link to numeric indices of dates
        self.graph_widget.getAxis("bottom").setTicks([list(enumerate(dates))])

        # Set y-axis ranges with some padding
        self.graph_widget.getViewBox().setYRange(0, self.max_weight * 1.1, padding=0)

        # Set the x-axis range for both views to ensure they align
        self.graph_widget.setXRange(0, len(dates) - 1)

        # Disable panning/zooming beyond the limits
        self.graph_widget.getViewBox().setLimits(
            xMin=0, xMax=len(dates) - 1, yMin=0, yMax=self.max_weight * 1.1
        )

        # Sync the right y-axis range to the left y-axis
        self.sync_right_y_axis()

    def show_graph_settings(self):
        """Shows the graph part of the settings menu"""
        # Clear the layout
        self.clear_settings_layout()

        # Create a grid layout
        graph_settings_grid = QGridLayout()

        # Add space in the first column
        space_item = QLabel(" ")
        graph_settings_grid.addWidget(space_item, 0, 0)

        # Header labels for Weight, Calories In, and Calories Out
        weight_label = QLabel("Weight")
        calories_in_label = QLabel("Calories In")
        calories_out_label = QLabel("Calories Out")
        graph_settings_grid.addWidget(weight_label, 0, 1)
        graph_settings_grid.addWidget(calories_in_label, 0, 2)
        graph_settings_grid.addWidget(calories_out_label, 0, 3)

        # Colour selection
        color_label = QLabel("Colour")
        self.weight_color_dropdown = QComboBox()
        self.weight_color_dropdown.addItems(["Red", "Blue", "Green", "Yellow", "Black", "White"])
        self.weight_color_dropdown.setCurrentText(self.weight_color)
        self.calories_in_color_dropdown = QComboBox()
        self.calories_in_color_dropdown.addItems(
            ["Red", "Blue", "Green", "Yellow", "Black", "White"]
        )
        self.calories_in_color_dropdown.setCurrentText(self.calories_in_color)
        self.calories_out_color_dropdown = QComboBox()
        self.calories_out_color_dropdown.addItems(
            ["Red", "Blue", "Green", "Yellow", "Black", "White"]
        )
        self.calories_out_color_dropdown.setCurrentText(self.calories_out_color)
        graph_settings_grid.addWidget(color_label, 1, 0)
        graph_settings_grid.addWidget(self.weight_color_dropdown, 1, 1)
        graph_settings_grid.addWidget(self.calories_in_color_dropdown, 1, 2)
        graph_settings_grid.addWidget(self.calories_out_color_dropdown, 1, 3)

        # Shape selection
        shape_label = QLabel("Shape")
        self.weight_shape_dropdown = QComboBox()
        self.weight_shape_dropdown.addItems(["Circle", "Square", "Triangle"])
        self.weight_shape_dropdown.setCurrentText(self.weight_shape)
        self.calories_in_shape_dropdown = QComboBox()
        self.calories_in_shape_dropdown.addItems(["Circle", "Square", "Triangle"])
        self.calories_in_shape_dropdown.setCurrentText(self.calories_in_shape)
        self.calories_out_shape_dropdown = QComboBox()
        self.calories_out_shape_dropdown.addItems(["Circle", "Square", "Triangle"])
        self.calories_out_shape_dropdown.setCurrentText(self.calories_out_shape)
        graph_settings_grid.addWidget(shape_label, 2, 0)
        graph_settings_grid.addWidget(self.weight_shape_dropdown, 2, 1)
        graph_settings_grid.addWidget(self.calories_in_shape_dropdown, 2, 2)
        graph_settings_grid.addWidget(self.calories_out_shape_dropdown, 2, 3)

        # Opacity input
        opacity_label = QLabel("Opacity")
        self.weight_opacity_input = QLineEdit()
        self.weight_opacity_input.setText(str(self.weight_opacity))
        self.calories_in_opacity_input = QLineEdit()
        self.calories_in_opacity_input.setText(str(self.calories_in_opacity))
        self.calories_out_opacity_input = QLineEdit()
        self.calories_out_opacity_input.setText(str(self.calories_out_opacity))
        graph_settings_grid.addWidget(opacity_label, 3, 0)
        graph_settings_grid.addWidget(self.weight_opacity_input, 3, 1)
        graph_settings_grid.addWidget(self.calories_in_opacity_input, 3, 2)
        graph_settings_grid.addWidget(self.calories_out_opacity_input, 3, 3)

        # Size input
        size_label = QLabel("Size")
        self.weight_size_input = QLineEdit()
        self.weight_size_input.setText(str(self.weight_size))
        self.calories_in_size_input = QLineEdit()
        self.calories_in_size_input.setText(str(self.calories_in_size))
        self.calories_out_size_input = QLineEdit()
        self.calories_out_size_input.setText(str(self.calories_out_size))
        graph_settings_grid.addWidget(size_label, 4, 0)
        graph_settings_grid.addWidget(self.weight_size_input, 4, 1)
        graph_settings_grid.addWidget(self.calories_in_size_input, 4, 2)
        graph_settings_grid.addWidget(self.calories_out_size_input, 4, 3)

        # Add Save and Cancel buttons at the bottom
        button_layout = QHBoxLayout()
        btn_save = QPushButton("Save")
        btn_cancel = QPushButton("Cancel")
        btn_save.clicked.connect(self.apply_graph_color_settings)
        btn_cancel.clicked.connect(self.settings_dialog.reject)
        button_layout.addWidget(btn_save)
        button_layout.addWidget(btn_cancel)

        # Add layout and buttons to the main settings layout
        self.settings_layout.addLayout(graph_settings_grid)
        self.settings_layout.addLayout(button_layout)

        # Adjust the size of the dialog window to fit the new layout
        self.settings_dialog.adjustSize()

    """
    
    Popup Forms for Food
    
    """

    def show_basic_food_form(self, edit=False, food_data=None, food_name=None):
        """Shows the input form for Basic food"""
        # Create the dialog for basic food
        self.new_food_dialog = QDialog(self)
        self.new_food_dialog.setWindowTitle("Edit Basic Food" if edit else "New Basic Food")

        # Layout
        self.new_food_layout = QVBoxLayout(self.new_food_dialog)

        label_1 = QLabel("Name")
        self.input_1 = QLineEdit()
        label_2 = QLabel("Calories per 100g")
        self.input_2 = QLineEdit()
        label_3 = QLabel("Protein per 100g")
        self.input_3 = QLineEdit()

        # If editing, populate the fields
        if edit and food_data:
            self.input_1.setText(food_name)
            self.input_2.setText(str(food_data[0]))  # Calories
            self.input_3.setText(str(food_data[1]))  # Protein

        # Add fields to the layout
        self.new_food_layout.addWidget(label_1)
        self.new_food_layout.addWidget(self.input_1)
        self.new_food_layout.addWidget(label_2)
        self.new_food_layout.addWidget(self.input_2)
        self.new_food_layout.addWidget(label_3)
        self.new_food_layout.addWidget(self.input_3)

        # Save and Cancel buttons
        btn_save = QPushButton("Save")
        btn_cancel = QPushButton("Cancel")
        btn_save.clicked.connect(self.update_basic_food if edit else self.save_basic_food)
        btn_cancel.clicked.connect(self.new_food_dialog.reject)

        button_layout = QHBoxLayout()
        button_layout.addWidget(btn_save)
        button_layout.addWidget(btn_cancel)
        self.new_food_layout.addLayout(button_layout)

        self.new_food_dialog.exec()

    def show_composite_food_form(self, edit=False, food_data=None, food_name=None):
        """Shows the input form for Composite food"""
        # Create the dialog for composite food
        self.new_food_dialog = QDialog(self)
        self.new_food_dialog.setWindowTitle("Edit Composite Food" if edit else "New Composite Food")

        # Layout
        self.new_food_layout = QVBoxLayout(self.new_food_dialog)

        label_1 = QLabel("Name")
        self.input_1 = QLineEdit()

        # If editing, populate the name
        if edit:
            self.input_1.setText(food_name)
        self.new_food_layout.addWidget(label_1)
        self.new_food_layout.addWidget(self.input_1)

        # Only include calories and protein fields if editing a composite food
        if edit:
            label_2 = QLabel("Calories per 100g")
            self.input_calories = QLabel(f"{food_data[1]:.2f}")
            label_3 = QLabel("Protein per 100g")
            self.input_protein = QLabel(f"{food_data[2]:.2f}")

            self.new_food_layout.addWidget(label_2)
            self.new_food_layout.addWidget(self.input_calories)
            self.new_food_layout.addWidget(label_3)
            self.new_food_layout.addWidget(self.input_protein)

        # Ingredient labels
        label_ingredients = QLabel("Ingredients:")
        self.new_food_layout.addWidget(label_ingredients)

        # Layout for ingredients
        self.composite_ingredient_rows = []
        ingredient_layout = QVBoxLayout()

        # If editing, populate the ingredient rows with the existing data
        if edit and food_data:
            ingredients = food_data[0].split(";")
            for ingredient in ingredients:
                name, quantity = ingredient.split(",")
                self.create_ingredient_row(ingredient_layout, name, quantity)
        else:
            # Add an initial empty row for new ingredient
            self.create_ingredient_row(ingredient_layout)

        self.new_food_layout.addLayout(ingredient_layout)

        # Button to add more ingredients
        btn_add_ingredient = QPushButton("Add Ingredient")
        btn_add_ingredient.clicked.connect(lambda: self.create_ingredient_row(ingredient_layout))
        self.new_food_layout.addWidget(btn_add_ingredient)

        # Save and Cancel buttons
        btn_save = QPushButton("Save")
        btn_cancel = QPushButton("Cancel")
        btn_save.clicked.connect(self.update_composite_food if edit else self.save_composite_food)
        btn_cancel.clicked.connect(self.new_food_dialog.reject)

        button_layout = QHBoxLayout()
        button_layout.addWidget(btn_save)
        button_layout.addWidget(btn_cancel)
        self.new_food_layout.addLayout(button_layout)

        self.new_food_dialog.exec()

    def create_ingredient_row(self, layout, ingredient_name="", quantity=""):
        """Creates an ingredient row to a composite food"""
        row_layout = QHBoxLayout()
        ingredient_dropdown = QComboBox()
        ingredient_dropdown.setEditable(True)
        # Populate the dropdown with foods
        self.populate_dropdown(ingredient_dropdown, "food")
        ingredient_dropdown.setCurrentText(ingredient_name)

        quantity_input = QLineEdit()
        quantity_input.setText(quantity)

        # Add the dropdown and input field to the row
        row_layout.addWidget(ingredient_dropdown)
        row_layout.addWidget(quantity_input)

        # Store the row in the composite_ingredient_rows list for later use
        self.composite_ingredient_rows.append((ingredient_dropdown, quantity_input))

        # Add the layout to the provided layout
        layout.addLayout(row_layout)

    def add_composite_ingredient_row(self):
        """Adds another ingredient row for a composite food"""
        row_layout = QHBoxLayout()

        dropdown = QComboBox()
        dropdown.setEditable(True)
        # Populate dropdown with foods
        self.populate_dropdown(dropdown, "food")

        quantity_input = QLineEdit()

        row_layout.addWidget(dropdown)
        row_layout.addWidget(quantity_input)

        # Store row
        self.composite_ingredient_rows.append((dropdown, quantity_input))

        # Add the new row to the ingredient rows layout
        self.ingredient_rows_layout.addLayout(row_layout)

    """
    
    Table and Data Handling
    
    """

    def calculate_daily_totals(self):
        """Calculate the total calories in and out per day and protein intake"""
        self.cursor.execute(
            "SELECT date, weight, food_consumed, exercises FROM daily_data ORDER BY date ASC"
        )
        records = self.cursor.fetchall()

        # Initialize a list to hold the rows for the table
        table_data = []
        previous_weight = None

        # Iterate the records in ascending date order
        for row in records:
            date, weight, food_consumed, exercises = row

            # Calories In and Protein calculation
            total_calories_in = 0
            total_protein = 0
            if food_consumed:
                foods = [tuple(item.split(",")) for item in food_consumed.split(";")]
                for food_name, amount in foods:
                    amount_in_grams = float(amount)
                    # Get the food's calories and protein from the database
                    self.cursor.execute(
                        "SELECT calories_per_100g, protein_per_100g FROM basic_food WHERE food_name = ? UNION SELECT calories_per_100g, protein_per_100g FROM composite_food WHERE food_name = ?",
                        (food_name, food_name),
                    )
                    food_data = self.cursor.fetchone()
                    if food_data:
                        calories_per_100g, protein_per_100g = food_data
                        total_calories_in += (calories_per_100g * amount_in_grams) / 100
                        total_protein += (protein_per_100g * amount_in_grams) / 100

            # Calories Out calculation from exercises
            total_calories_out = 0
            if exercises:
                exercise_list = [tuple(item.split(",")) for item in exercises.split(";")]
                for exercise, calories in exercise_list:
                    total_calories_out += float(calories)

            # Calculate prior weight difference
            prior_diff = "N/A"
            if weight is not None and previous_weight is not None:
                prior_diff = f"{weight - previous_weight:.2f}"

            # Calculate goal weight difference (weight - goal)
            goal_diff = f"{weight - Goal:.2f}" if weight is not None else "N/A"

            # Prepare the row for the table
            table_data.append(
                [
                    date,
                    f"{weight}" if weight is not None else "N/A",
                    f"{total_calories_in:.0f}",
                    f"{total_calories_out:.0f}",
                    f"{total_protein:.0f}",
                    prior_diff,
                    goal_diff,
                ]
            )

            # Update previous_weight for the next iteration
            previous_weight = weight

        # Reverse the list for display
        return table_data[::-1]

    def update_table(self):
        """Updates the table to reflect any changes"""
        # Fetch the calculated table data
        table_data = self.calculate_daily_totals()

        # Update the table widget
        self.table.setRowCount(len(table_data))
        for row_idx, row_data in enumerate(table_data):
            try:
                # Extract weight from the row
                weight = float(row_data[1]) if row_data[1] != "N/A" else None

                # Extract protein intake
                protein = float(row_data[4]) if row_data[4] != "N/A" else 0
            except ValueError:
                # In case of errors
                weight = None
                protein = 0

            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                # Check if the current column is the 'Protein (g)' column and if weight is valid
                if col_idx == 4 and weight is not None:
                    # Check if protein intake is below 0.8 * weight
                    if protein < 0.8 * weight:
                        item.setForeground(QColor("red"))  # Set text color to red
                    else:
                        item.setForeground(QColor("white"))  # Set text color back to default

                # Add item to the table
                self.table.setItem(row_idx, col_idx, item)

        # Adjust rows and columns to fit the content
        self.table.resizeRowsToContents()
        self.table.resizeColumnsToContents()

        # Update the graph
        self.update_graph()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    app.setWindowIcon(QIcon("icon.ico"))
    window.show()
    sys.exit(app.exec())
