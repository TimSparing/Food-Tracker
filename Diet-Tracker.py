from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QComboBox, QSpacerItem,
                             QSizePolicy, QDialog, QCalendarWidget, QGridLayout)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor, QIcon
import sys
import pyqtgraph as pg
import os
import sqlite3

ButtonWidth = 80
InputWidth = 125
Goal = 80

# Helper function to convert color name to QColor or RGB(A) tuple


class CustomAxisItem(pg.AxisItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_angle = -60  # Set the default label angle

    def tickStrings(self, values, scale, spacing):
        """Override tickStrings to format axis labels."""
        strings = super().tickStrings(values, scale, spacing)
        return strings

    def drawPicture(self, p, axisSpec, tickSpecs, textSpecs):
        """
        Override drawPicture to apply rotation to x-axis text.
        """
        # Call the base class method to draw the axis line and ticks, but no labels
        super().drawPicture(p, axisSpec, tickSpecs, [])

        # Offset for positioning the labels
        x_offset = -26
        y_offset = -3  # Adjust based on your padding needs

        # Custom text drawing with rotation
        for rect, flags, text in textSpecs:
            p.save()  # Save painter state
            p.setClipping(False)  # Disable clipping to avoid partial drawing

            # Move to the center of the text rect for rotation
            p.translate(rect.center())
            p.rotate(self.label_angle)  # Apply rotation
            p.translate(-rect.center())

            # Apply offset for custom positioning
            p.translate(x_offset, y_offset)

            # Draw the rotated text
            p.drawText(rect, flags, text)
            p.restore()  # Restore painter state


def get_color_from_name(color_name, opacity=255):
    color = QColor(color_name)
    if color.isValid():
        return (color.red(), color.green(), color.blue(), opacity)
    else:
        # Fallback to a default color, e.g., black, if color_name is invalid
        return (0, 0, 0, opacity)


def get_shape_symbol(shape_name):
    """Helper function to map shape names to PyQtGraph symbols."""
    if shape_name == 'Circle':
        return 'o'
    elif shape_name == 'Square':
        return 's'
    elif shape_name == 'Triangle':
        return 't'
    else:
        return 'o'  # Default to Circle if not recognized


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Initialize the database before anything else
        self.initialize_database()

        # Set the window title and size
        self.setWindowTitle("Food Tracker")
        self.setGeometry(100, 100, 1000, 600)
        self.setWindowIcon(QIcon("icon.ico"))

        # Main Widget and Layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QHBoxLayout(main_widget)

        # Left side layout (for table and inputs)
        left_layout = QVBoxLayout()

        # Create table
        self.create_table(left_layout)

        # Create input fields, buttons, etc.
        self.create_input_section(left_layout)

        # Right side for graph with dummy data
        graph_widget = self.create_graph()  # Ensure graph is created before settings
        self.main_layout.addLayout(left_layout)
        self.main_layout.addWidget(graph_widget, stretch=1)  # Let the graph expand horizontally

        # Load settings from the database (now after graph initialization)
        self.load_settings()

        # Initialize the selected date after table creation
        self.selected_date = QDate.currentDate()

        self.new_food_layout = None
        # Update the table
        self.update_table()

        # Highlight today's date after table is updated
        self.highlight_selected_date()

    def initialize_database(self):
        # Check if the database already exists, if not create one
        db_exists = os.path.exists("database.db")

        # Connect to the SQLite database (it will create the file if it doesn't exist)
        self.conn = sqlite3.connect("database.db")
        self.cursor = self.conn.cursor()

        # Create tables if the database is new
        if not db_exists:
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
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
                                    calories_out_size REAL)''')

            self.cursor.execute('''CREATE TABLE IF NOT EXISTS basic_food (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    food_name TEXT,
                                    calories_per_100g REAL,
                                    protein_per_100g REAL)''')

            self.cursor.execute('''CREATE TABLE IF NOT EXISTS composite_food (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    food_name TEXT,
                                    ingredients TEXT,  -- Stores the list of ingredients in format (name, amount)
                                    calories_per_100g REAL,
                                    protein_per_100g REAL)''')

            self.cursor.execute('''CREATE TABLE IF NOT EXISTS daily_data (
                                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        date TEXT UNIQUE,
                                        weight REAL,
                                        food_consumed TEXT,  -- This stores a list of foods and amounts in format (name, amount)
                                        exercises TEXT)''')  # This stores a list of exercises and calories burned

            # Insert default settings (can be modified later by the user)
            self.cursor.execute('''INSERT INTO settings (line1_color, line2_color, font_size, font_type,
                                                         weight_color, weight_shape, weight_opacity, weight_size,
                                                         calories_in_color, calories_in_shape, calories_in_opacity, calories_in_size,
                                                         calories_out_color, calories_out_shape, calories_out_opacity, calories_out_size)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                ('blue', 'red', 'Medium', 'Arial',  # Default font settings
                                 'blue', 'Circle', 100, 10,  # Default graph settings for weight
                                 'green', 'Square', 100, 10,  # Default graph settings for calories in
                                 'red', 'Triangle', 100, 10))  # Default graph settings for calories out
            self.conn.commit()

    def add_missing_columns(self):
        """Helper function to add missing columns to the settings table."""
        # List of new columns and their default values
        columns_to_add = [
            ("weight_color", "TEXT", "'blue'"),
            ("weight_shape", "TEXT", "'Circle'"),
            ("weight_opacity", "REAL", "100"),
            ("weight_size", "REAL", "10"),
            ("calories_in_color", "TEXT", "'green'"),
            ("calories_in_shape", "TEXT", "'Square'"),
            ("calories_in_opacity", "REAL", "100"),
            ("calories_in_size", "REAL", "10"),
            ("calories_out_color", "TEXT", "'red'"),
            ("calories_out_shape", "TEXT", "'Triangle'"),
            ("calories_out_opacity", "REAL", "100"),
            ("calories_out_size", "REAL", "10")
        ]

        # Check if each column exists and add if not
        for column_name, column_type, default_value in columns_to_add:
            try:
                self.cursor.execute(
                    f"ALTER TABLE settings ADD COLUMN {column_name} {column_type} DEFAULT {default_value}")
            except sqlite3.OperationalError:
                # Column already exists, continue to the next one
                continue
        self.conn.commit()

    def load_settings(self):
        # Fetch the settings from the database
        self.cursor.execute('''SELECT line1_color, line2_color, font_size, font_type,
                                      weight_color, weight_shape, weight_opacity, weight_size,
                                      calories_in_color, calories_in_shape, calories_in_opacity, calories_in_size,
                                      calories_out_color, calories_out_shape, calories_out_opacity, calories_out_size
                               FROM settings LIMIT 1''')
        settings = self.cursor.fetchone()

        if settings:
            (self.line1_color, self.line2_color, self.font_size, self.font_type,
             self.weight_color, self.weight_shape, self.weight_opacity, self.weight_size,
             self.calories_in_color, self.calories_in_shape, self.calories_in_opacity, self.calories_in_size,
             self.calories_out_color, self.calories_out_shape, self.calories_out_opacity, self.calories_out_size) = settings

            # Apply settings to the graph and font
            self.apply_font_to_widgets(self.font_type, self.font_size)
        else:
            # If no settings found, apply default values
            self.line1_color = 'blue'
            self.line2_color = 'red'
            self.font_size = 'Medium'
            self.font_type = 'Arial'
            self.weight_color = 'blue'
            self.weight_shape = 'Circle'
            self.weight_opacity = 100
            self.weight_size = 10
            self.calories_in_color = 'green'
            self.calories_in_shape = 'Square'
            self.calories_in_opacity = 100
            self.calories_in_size = 10
            self.calories_out_color = 'red'
            self.calories_out_shape = 'Triangle'
            self.calories_out_opacity = 100
            self.calories_out_size = 10

    def closeEvent(self, event):
        # Ensure that the connection to the database is properly closed
        self.conn.close()
        event.accept()

    def save_weight(self):
        weight = self.input_field_1.text()
        if weight:
            weight = float(weight)
            # Fetch existing data for the selected date
            self.cursor.execute('SELECT food_consumed, exercises FROM daily_data WHERE date = ?',
                                (self.selected_date.toString(Qt.DateFormat.ISODate),))
            existing_data = self.cursor.fetchone()

            if existing_data:
                food_consumed, exercises = existing_data
            else:
                food_consumed, exercises = "", ""  # Initialize if no data exists

            # Update the database with the new weight, while keeping the food and exercises unchanged
            self.cursor.execute('INSERT OR REPLACE INTO daily_data (date, weight, food_consumed, exercises) VALUES (?, ?, ?, ?)',
                                (self.selected_date.toString(Qt.DateFormat.ISODate), weight, food_consumed, exercises))
            self.conn.commit()
            self.update_table()  # Update the table to reflect the new data
            self.update_graph()

    def save_food(self):
        food = self.dropdown_2.currentText()
        quantity = self.input_field_3.text()
        if food and quantity:
            quantity = float(quantity)
            # Fetch existing data for the selected date
            self.cursor.execute('SELECT weight, exercises, food_consumed FROM daily_data WHERE date = ?',
                                (self.selected_date.toString(Qt.DateFormat.ISODate),))
            existing_data = self.cursor.fetchone()

            if existing_data:
                weight, exercises, food_consumed = existing_data
            else:
                weight, exercises, food_consumed = None, "", ""  # Initialize if no data exists

            food_str = f"{food},{quantity}"
            if food_consumed:
                # Append to existing food entries
                new_food = food_consumed + f";{food_str}"
            else:
                new_food = food_str

            # Update the database with the new food data, keeping other data unchanged
            self.cursor.execute('INSERT OR REPLACE INTO daily_data (date, weight, food_consumed, exercises) VALUES (?, ?, ?, ?)',
                                (self.selected_date.toString(Qt.DateFormat.ISODate), weight, new_food, exercises))
            self.conn.commit()
            self.update_table()  # Update the table to reflect the new data
            self.update_graph()

    def save_exercise(self):
        exercise = self.dropdown_1.currentText()
        calories = self.input_field_2.text()
        if exercise and calories:
            calories = float(calories)
            # Fetch existing data for the selected date
            self.cursor.execute('SELECT weight, food_consumed, exercises FROM daily_data WHERE date = ?',
                                (self.selected_date.toString(Qt.DateFormat.ISODate),))
            existing_data = self.cursor.fetchone()

            if existing_data:
                weight, food_consumed, exercises = existing_data
            else:
                weight, food_consumed, exercises = None, "", ""  # Initialize if no data exists

            exercise_str = f"{exercise},{calories}"
            if exercises:
                # Append to existing exercises
                new_exercises = exercises + f";{exercise_str}"
            else:
                new_exercises = exercise_str

            # Update the database with the new exercise data, keeping other data unchanged
            self.cursor.execute('INSERT OR REPLACE INTO daily_data (date, weight, food_consumed, exercises) VALUES (?, ?, ?, ?)',
                                (self.selected_date.toString(Qt.DateFormat.ISODate), weight, food_consumed, new_exercises))
            self.conn.commit()
            self.update_table()  # Update the table to reflect the new data
            self.update_graph()

    def calculate_food_quantity(self):
        food = self.dropdown_2.currentText()
        calories = self.input_field_4.text()
        if food and calories:
            calories = float(calories)
            # Fetch the food's calorie data from the database
            self.cursor.execute(
                'SELECT calories_per_100g FROM basic_food WHERE food_name = ? UNION SELECT calories_per_100g FROM composite_food WHERE food_name = ?', (food, food))
            food_data = self.cursor.fetchone()
            if food_data:
                calories_per_100g = food_data[0]
                if calories_per_100g > 0:
                    quantity = (calories / calories_per_100g) * 100
                    # Display the calculated quantity in the quantity input field
                    self.input_field_3.setText(f"{quantity:.2f}")

    def highlight_selected_date(self):
        """Highlight the row in the table corresponding to the selected date."""
        # Format the selected date as a string (ISO format: YYYY-MM-DD)
        selected_date_str = self.selected_date.toString(Qt.DateFormat.ISODate)

        # Search through the table rows to find a matching date
        for row in range(self.table.rowCount()):
            date_item = self.table.item(row, 0)  # The date is in the first column
            if date_item and date_item.text() == selected_date_str:
                self.table.selectRow(row)  # Select the matching row
                return
        # If no matching date is found, clear the selection
        self.table.clearSelection()

    def move_to_previous_day(self):
        """Move the selected date back by 1 day."""
        self.selected_date = self.selected_date.addDays(-1)
        self.highlight_selected_date()

    def move_to_next_day(self):
        """Move the selected date forward by 1 day."""
        self.selected_date = self.selected_date.addDays(1)
        self.highlight_selected_date()

    def save_settings(self, line1_color=None, line2_color=None, font_size=None, font_type=None):
        # Update only the provided settings
        if line1_color:
            self.line1_color = line1_color
        if line2_color:
            self.line2_color = line2_color
        if font_size:
            self.font_size = font_size
        if font_type:
            self.font_type = font_type

        # Save the updated settings in the database, including graph settings
        self.cursor.execute('''UPDATE settings SET
                                line1_color = ?, line2_color = ?, font_size = ?, font_type = ?,
                                weight_color = ?, weight_shape = ?, weight_opacity = ?, weight_size = ?,
                                calories_in_color = ?, calories_in_shape = ?, calories_in_opacity = ?, calories_in_size = ?,
                                calories_out_color = ?, calories_out_shape = ?, calories_out_opacity = ?, calories_out_size = ?''',
                            (self.line1_color, self.line2_color, self.font_size, self.font_type,
                             self.weight_color, self.weight_shape, self.weight_opacity, self.weight_size,
                             self.calories_in_color, self.calories_in_shape, self.calories_in_opacity, self.calories_in_size,
                             self.calories_out_color, self.calories_out_shape, self.calories_out_opacity, self.calories_out_size))
        self.conn.commit()

    def apply_graph_color_settings(self):
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

        # Update the graph based on the new settings
        self.update_graph()

        # Close the settings dialog
        self.settings_dialog.accept()

    def apply_font_settings(self):
        font_type = self.dropdown_font_type.currentText()
        font_size = self.dropdown_font_size.currentText()
        self.apply_font_to_widgets(font_type, font_size)

        # Save the font settings to the database
        self.save_settings(font_size=font_size, font_type=font_type)
        self.settings_dialog.accept()

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())

    def show_settings_popup(self):
        # Create a QDialog for the settings popup
        self.settings_dialog = QDialog(self)
        self.settings_dialog.setWindowTitle("Settings")

        # Create a layout for the settings
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

    def show_edit_food(self):
        # Clear the settings layout
        self.clear_settings_layout()

        # Dropdown for selecting the food to edit
        self.food_dropdown = QComboBox()
        self.food_dropdown.setEditable(True)

        # Populate the dropdown with all available foods
        self.populate_dropdown(self.food_dropdown, "food")

        # Buttons to load the selected food or cancel
        btn_load = QPushButton("Edit")
        btn_cancel = QPushButton("Cancel")
        btn_load.clicked.connect(self.load_food_for_edit)
        btn_cancel.clicked.connect(self.settings_dialog.reject)

        # Layout for the Edit Food section
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
        # Clear the settings layout
        self.clear_settings_layout()

        # Calendar for selecting the date
        self.calendar = QCalendarWidget()
        self.calendar.setSelectedDate(QDate.currentDate())  # Default to current date

        # Buttons to load the data for the selected date or cancel
        btn_edit = QPushButton("Edit")
        btn_cancel = QPushButton("Cancel")
        btn_edit.clicked.connect(self.load_data_for_date)
        btn_cancel.clicked.connect(self.settings_dialog.reject)

        # Layout for the Edit Date section
        layout = QVBoxLayout()
        layout.addWidget(self.calendar)

        button_layout = QHBoxLayout()
        button_layout.addWidget(btn_edit)
        button_layout.addWidget(btn_cancel)

        layout.addLayout(button_layout)

        self.settings_layout.addLayout(layout)
        self.settings_dialog.adjustSize()

    def load_data_for_date(self):
        selected_date = self.calendar.selectedDate().toString(Qt.DateFormat.ISODate)

        # Fetch data from the database for the selected date
        self.cursor.execute('SELECT weight, food_consumed, exercises FROM daily_data WHERE date = ?', (selected_date,))
        data = self.cursor.fetchone()

        if data:
            weight, food_consumed, exercises = data
        else:
            weight, food_consumed, exercises = None, "", ""

        # Pass the data to a new method for displaying the form
        self.show_date_data_form(selected_date, weight, food_consumed, exercises)

    def refresh_food_dropdowns(self):
        """Refresh all food dropdowns with updated data from the database."""
        self.dropdown_2.clear()  # Clear the existing dropdown items for food

        # Fetch all the food items from the basic and composite food tables
        self.cursor.execute("SELECT food_name FROM basic_food UNION SELECT food_name FROM composite_food")
        foods = self.cursor.fetchall()

        # Add the new food items to the dropdown
        for food in foods:
            self.dropdown_2.addItem(food[0])

        # If you have other food dropdowns in the app (e.g., in a food edit form), refresh those too.

    def show_date_data_form(self, date, weight=None, food_consumed="", exercises=""):
        # Clear the settings layout
        self.clear_settings_layout()

        # Add a new layout for the date data
        self.date_data_layout = QVBoxLayout()

        # Weight input field
        self.weight_input = QLineEdit()
        self.weight_input.setText(f"{weight}" if weight else "")
        weight_layout = QHBoxLayout()
        weight_layout.addWidget(QLabel("Weight:"))
        weight_layout.addWidget(self.weight_input)

        # Ensure the weight layout is the first item added
        self.date_data_layout.addLayout(weight_layout)

        # Create sub-layouts for food and exercise entries
        self.food_layout = QVBoxLayout()
        self.exercise_layout = QVBoxLayout()

        # Section for food entries
        self.food_rows = []
        food_list = [tuple(item.split(',')) for item in food_consumed.split(';')] if food_consumed else []
        for food_name, amount in food_list:
            self.add_food_row(food_name, amount)

        # Section for exercise entries
        self.exercise_rows = []
        exercise_list = [tuple(item.split(',')) for item in exercises.split(';')] if exercises else []
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

        # Finally, add the entire layout to the dialog
        self.settings_layout.addLayout(self.date_data_layout)

        # Force the window to adjust size after adding the elements
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
        self.food_layout.addLayout(row_layout)  # Add the row to the food_layout

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
        self.exercise_layout.addLayout(row_layout)  # Add the row to the exercise_layout

    def populate_dropdown(self, dropdown, type):
        """Populate a dropdown menu with food or exercise entries from the database"""
        dropdown.clear()  # Clear existing items before populating

        if type == "food":
            # Fetch all food items from both basic and composite food tables
            self.cursor.execute("SELECT food_name FROM basic_food UNION SELECT food_name FROM composite_food")
            foods = self.cursor.fetchall()
            for food in foods:
                dropdown.addItem(food[0])
        elif type == "exercise":
            # Predefined exercise options
            exercises = ["Cycling", "Swimming", "Jogging", "Climbing", "Weight Training"]
            for exercise in exercises:
                dropdown.addItem(exercise)

    def load_daily_data(self, date):
        """Load the weight, food, and exercises for the selected date"""
        self.cursor.execute('SELECT weight, food_consumed, exercises FROM daily_data WHERE date = ?', (date,))
        data = self.cursor.fetchone()

        if data:
            weight, food_consumed, exercises = data

            # Process food data
            food_list = []
            if food_consumed:
                try:
                    food_list = [tuple(item.split(',')) for item in food_consumed.split(';')]
                except ValueError:
                    pass  # Handle any improperly formatted food data

            # Process exercise data
            exercise_list = []
            if exercises:
                try:
                    exercise_list = [tuple(item.split(',')) for item in exercises.split(';')]
                except ValueError:
                    pass  # Handle any improperly formatted exercise data

            return weight, food_list, exercise_list

        return None, [], []  # Return empty data if no record is found

    def save_date_data(self, date):
        """Save or update the date's data in the database"""

        # Get the weight input
        weight = self.weight_input.text()
        weight = float(weight) if weight else None  # Remove from DB if empty

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

        # Update the main table to reflect changes
        self.update_table()
        self.update_graph()

        # Close the dialog
        self.settings_dialog.accept()

    def show_graph_settings(self):
        # Clear the settings layout
        self.clear_settings_layout()

        # Create a grid layout to align the settings properly
        graph_settings_grid = QGridLayout()

        # Add space in the first column for labels
        space_item = QLabel(" ")
        graph_settings_grid.addWidget(space_item, 0, 0)  # Add space in the first row, first column

        # Header labels for Weight, Calories In, and Calories Out
        weight_label = QLabel("Weight")
        calories_in_label = QLabel("Calories In")
        calories_out_label = QLabel("Calories Out")
        graph_settings_grid.addWidget(weight_label, 0, 1)
        graph_settings_grid.addWidget(calories_in_label, 0, 2)
        graph_settings_grid.addWidget(calories_out_label, 0, 3)

        # Row 1: Color selection
        color_label = QLabel("Color")
        self.weight_color_dropdown = QComboBox()
        self.weight_color_dropdown.addItems(["Red", "Blue", "Green", "Yellow", "Black"])
        self.weight_color_dropdown.setCurrentText(self.weight_color)  # Set current value
        self.calories_in_color_dropdown = QComboBox()
        self.calories_in_color_dropdown.addItems(["Red", "Blue", "Green", "Yellow", "Black"])
        self.calories_in_color_dropdown.setCurrentText(self.calories_in_color)  # Set current value
        self.calories_out_color_dropdown = QComboBox()
        self.calories_out_color_dropdown.addItems(["Red", "Blue", "Green", "Yellow", "Black"])
        self.calories_out_color_dropdown.setCurrentText(self.calories_out_color)  # Set current value
        graph_settings_grid.addWidget(color_label, 1, 0)
        graph_settings_grid.addWidget(self.weight_color_dropdown, 1, 1)
        graph_settings_grid.addWidget(self.calories_in_color_dropdown, 1, 2)
        graph_settings_grid.addWidget(self.calories_out_color_dropdown, 1, 3)

        # Row 2: Shape selection
        shape_label = QLabel("Shape")
        self.weight_shape_dropdown = QComboBox()
        self.weight_shape_dropdown.addItems(["Circle", "Square", "Triangle"])
        self.weight_shape_dropdown.setCurrentText(self.weight_shape)  # Set current value
        self.calories_in_shape_dropdown = QComboBox()
        self.calories_in_shape_dropdown.addItems(["Circle", "Square", "Triangle"])
        self.calories_in_shape_dropdown.setCurrentText(self.calories_in_shape)  # Set current value
        self.calories_out_shape_dropdown = QComboBox()
        self.calories_out_shape_dropdown.addItems(["Circle", "Square", "Triangle"])
        self.calories_out_shape_dropdown.setCurrentText(self.calories_out_shape)  # Set current value
        graph_settings_grid.addWidget(shape_label, 2, 0)
        graph_settings_grid.addWidget(self.weight_shape_dropdown, 2, 1)
        graph_settings_grid.addWidget(self.calories_in_shape_dropdown, 2, 2)
        graph_settings_grid.addWidget(self.calories_out_shape_dropdown, 2, 3)

        # Row 3: Opacity input
        opacity_label = QLabel("Opacity")
        self.weight_opacity_input = QLineEdit()
        self.weight_opacity_input.setText(str(self.weight_opacity))  # Set current value
        self.calories_in_opacity_input = QLineEdit()
        self.calories_in_opacity_input.setText(str(self.calories_in_opacity))  # Set current value
        self.calories_out_opacity_input = QLineEdit()
        self.calories_out_opacity_input.setText(str(self.calories_out_opacity))  # Set current value
        graph_settings_grid.addWidget(opacity_label, 3, 0)
        graph_settings_grid.addWidget(self.weight_opacity_input, 3, 1)
        graph_settings_grid.addWidget(self.calories_in_opacity_input, 3, 2)
        graph_settings_grid.addWidget(self.calories_out_opacity_input, 3, 3)

        # Row 4: Size input
        size_label = QLabel("Size")
        self.weight_size_input = QLineEdit()
        self.weight_size_input.setText(str(self.weight_size))  # Set current value
        self.calories_in_size_input = QLineEdit()
        self.calories_in_size_input.setText(str(self.calories_in_size))  # Set current value
        self.calories_out_size_input = QLineEdit()
        self.calories_out_size_input.setText(str(self.calories_out_size))  # Set current value
        graph_settings_grid.addWidget(size_label, 4, 0)
        graph_settings_grid.addWidget(self.weight_size_input, 4, 1)
        graph_settings_grid.addWidget(self.calories_in_size_input, 4, 2)
        graph_settings_grid.addWidget(self.calories_out_size_input, 4, 3)

        # Add Save and Cancel buttons at the bottom
        button_layout = QHBoxLayout()
        btn_save = QPushButton("Save")
        btn_cancel = QPushButton("Cancel")
        btn_save.clicked.connect(self.apply_graph_color_settings)  # Apply changes and save
        btn_cancel.clicked.connect(self.settings_dialog.reject)
        button_layout.addWidget(btn_save)
        button_layout.addWidget(btn_cancel)

        # Add the grid layout and buttons to the main settings layout
        self.settings_layout.addLayout(graph_settings_grid)
        self.settings_layout.addLayout(button_layout)

        # Adjust the size of the dialog window to fit the new layout
        self.settings_dialog.adjustSize()

    def show_font_settings(self):
        # Clear the settings layout
        self.clear_settings_layout()

        # Dropdown menus for font size and font type
        self.dropdown_font_size = QComboBox()
        self.dropdown_font_type = QComboBox()

        # Populate with some example font sizes and types
        font_sizes = ["Small", "Medium", "Large"]
        font_types = ["Arial", "Helvetica", "Times New Roman", "Courier"]

        self.dropdown_font_size.addItems(font_sizes)
        self.dropdown_font_type.addItems(font_types)

        # Buttons to save or cancel
        btn_save = QPushButton("Save")
        btn_cancel = QPushButton("Cancel")
        btn_save.clicked.connect(self.apply_font_settings)  # Apply font settings
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
        # Adjust the font size based on selection
        if font_size == "Small":
            point_size = 10
        elif font_size == "Medium":
            point_size = 14
        elif font_size == "Large":
            point_size = 18

        # Create the QFont object with the selected font and size
        font = QFont(font_type, point_size)

        # Apply the font to the main window and all widgets
        self.setFont(font)

    def clear_settings_layout(self):
        while self.settings_layout.count():
            item = self.settings_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())

    def show_new_food_popup(self):
        # Create a QDialog for the new food popup
        self.new_food_dialog = QDialog(self)
        self.new_food_dialog.setWindowTitle("New Food Entry")

        # Create a main layout for the dialog
        self.new_food_layout = QVBoxLayout()

        # Show the initial selection buttons for "Basic" and "Composite"
        self.show_initial_food_buttons()

        # Set the dialog layout
        self.new_food_dialog.setLayout(self.new_food_layout)
        self.new_food_dialog.exec()

    def show_initial_food_buttons(self):
        # Clear any existing layout to prevent overlap
        self.clear_new_food_layout()

        # Buttons for selecting "Basic" or "Composite"
        btn_basic = QPushButton("Basic")
        btn_composite = QPushButton("Composite")

        # Connect buttons to respective layout functions
        btn_basic.clicked.connect(self.show_basic_food_form)
        btn_composite.clicked.connect(self.show_composite_food_form)

        # Add buttons to the layout
        button_layout = QHBoxLayout()
        button_layout.addWidget(btn_basic)
        button_layout.addWidget(btn_composite)

        # Add button layout to the main layout
        self.new_food_layout.addLayout(button_layout)

    def clear_new_food_layout(self):
        while self.new_food_layout.count():
            item = self.new_food_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())

    def load_food_for_edit(self):
        selected_food = self.food_dropdown.currentText()

        if not selected_food:
            return  # Do nothing if no food is selected

        # Check if the food is Basic or Composite
        self.cursor.execute(
            'SELECT calories_per_100g, protein_per_100g FROM basic_food WHERE food_name = ?', (selected_food,))
        basic_food = self.cursor.fetchone()

        if basic_food:
            # If it's a Basic food, load the Basic food form with pre-filled data
            self.show_basic_food_form(edit=True, food_data=basic_food, food_name=selected_food)
        else:
            # Check if it's a Composite food
            self.cursor.execute(
                'SELECT ingredients, calories_per_100g, protein_per_100g FROM composite_food WHERE food_name = ?', (selected_food,))
            composite_food = self.cursor.fetchone()

            if composite_food:
                # If it's a Composite food, load the Composite food form with pre-filled data
                self.show_composite_food_form(edit=True, food_data=composite_food, food_name=selected_food)

    def show_basic_food_form(self, edit=False, food_data=None, food_name=None):
        # Create the dialog for basic food
        self.new_food_dialog = QDialog(self)
        self.new_food_dialog.setWindowTitle("Edit Basic Food" if edit else "New Basic Food")

        # Layout for the basic food form
        self.new_food_layout = QVBoxLayout(self.new_food_dialog)

        label_1 = QLabel("Name")
        self.input_1 = QLineEdit()  # Name input
        label_2 = QLabel("Calories per 100g")
        self.input_2 = QLineEdit()  # Calories input
        label_3 = QLabel("Protein per 100g")
        self.input_3 = QLineEdit()  # Protein input

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

        self.new_food_dialog.exec()  # Open the dialog

    def show_composite_food_form(self, edit=False, food_data=None, food_name=None):
        # Create the dialog for composite food
        self.new_food_dialog = QDialog(self)
        self.new_food_dialog.setWindowTitle("Edit Composite Food" if edit else "New Composite Food")

        # Layout for the composite food form
        self.new_food_layout = QVBoxLayout(self.new_food_dialog)

        label_1 = QLabel("Name")
        self.input_1 = QLineEdit()  # Name input

        # If editing, populate the name and make it editable
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
        self.composite_ingredient_rows = []  # Initialize list to track ingredient rows
        ingredient_layout = QVBoxLayout()

        # If editing, populate the ingredient rows with the existing data
        if edit and food_data:
            ingredients = food_data[0].split(';')  # Ingredients string from database
            for ingredient in ingredients:
                name, quantity = ingredient.split(',')
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

        self.new_food_dialog.exec()  # Open the dialog

    def create_ingredient_row(self, layout, ingredient_name="", quantity=""):
        # Create a row for an ingredient entry with name and quantity fields
        row_layout = QHBoxLayout()
        ingredient_dropdown = QComboBox()
        ingredient_dropdown.setEditable(True)  # Allow user to type/select a food
        self.populate_dropdown(ingredient_dropdown, "food")  # Populate the dropdown with foods
        ingredient_dropdown.setCurrentText(ingredient_name)

        quantity_input = QLineEdit()
        quantity_input.setText(quantity)

        # Add the dropdown and input field to the row
        row_layout.addWidget(ingredient_dropdown)
        row_layout.addWidget(quantity_input)

        # Store the row in the composite_ingredient_rows list for later use
        self.composite_ingredient_rows.append((ingredient_dropdown, quantity_input))

        # Add the row layout to the provided layout
        layout.addLayout(row_layout)

    def update_basic_food(self):
        new_food_name = self.input_1.text().strip()
        calories = self.input_2.text().strip()
        protein = self.input_3.text().strip()
        old_food_name = self.food_dropdown.currentText().strip()  # The original name selected from the dropdown

        if new_food_name and calories and protein:
            # Check if the new food name already exists (to avoid duplicate names)
            self.cursor.execute('SELECT food_name FROM basic_food WHERE food_name = ?', (new_food_name,))
            existing_food = self.cursor.fetchone()

            if existing_food is None or new_food_name == old_food_name:
                # If the new name doesn't exist or the name is the same, update the record
                self.cursor.execute('''UPDATE basic_food
                                       SET food_name = ?, calories_per_100g = ?, protein_per_100g = ?
                                       WHERE food_name = ?''',
                                    (new_food_name, float(calories), float(protein), old_food_name))
                self.conn.commit()

                self.refresh_food_dropdowns()  # Refresh dropdowns after updating the food
                self.new_food_dialog.accept()  # Close the dialog
            else:
                # Show a message that the new name already exists
                print("A food with this name already exists. Please choose a different name.")

    def update_composite_food(self):
        new_composite_name = self.input_1.text().strip()
        old_composite_name = self.food_dropdown.currentText().strip()  # The original name selected from the dropdown
        ingredients = []
        total_calories = 0
        total_protein = 0
        total_weight = 0

        # Loop through each ingredient row and collect data
        for dropdown, quantity_input in self.composite_ingredient_rows:
            ingredient_name = dropdown.currentText().strip()
            quantity = quantity_input.text().strip()

            if ingredient_name and quantity:
                self.cursor.execute('''SELECT calories_per_100g, protein_per_100g
                                       FROM basic_food WHERE food_name = ?
                                       UNION SELECT calories_per_100g, protein_per_100g
                                       FROM composite_food WHERE food_name = ?''',
                                    (ingredient_name, ingredient_name))
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

            ingredients_str = ';'.join([f"{name},{amount}" for name, amount in ingredients])

            # Check if the new name already exists
            self.cursor.execute('SELECT food_name FROM composite_food WHERE food_name = ?', (new_composite_name,))
            existing_food = self.cursor.fetchone()

            if existing_food is None or new_composite_name == old_composite_name:
                # Update the composite food in the database
                self.cursor.execute('''UPDATE composite_food
                                       SET food_name = ?, ingredients = ?, calories_per_100g = ?, protein_per_100g = ?
                                       WHERE food_name = ?''',
                                    (new_composite_name, ingredients_str, composite_calories_per_100g, composite_protein_per_100g, old_composite_name))
                self.conn.commit()

                self.refresh_food_dropdowns()  # Refresh dropdowns to show the newly updated food
                self.new_food_dialog.accept()  # Close the dialog
            else:
                # Show a message that the new name already exists
                print("A composite food with this name already exists. Please choose a different name.")

    def calculate_daily_totals(self):
        # Query to get all the dates and their respective data from the database in ascending order by date
        self.cursor.execute('SELECT date, weight, food_consumed, exercises FROM daily_data ORDER BY date ASC')
        records = self.cursor.fetchall()

        # Initialize a list to hold the rows for the table
        table_data = []
        previous_weight = None  # To calculate the difference with the previous day's weight

        # Iterate the records in ascending date order (oldest first)
        for row in records:
            date, weight, food_consumed, exercises = row

            # Calories In and Protein calculation
            total_calories_in = 0
            total_protein = 0
            if food_consumed:
                foods = [tuple(item.split(',')) for item in food_consumed.split(';')]
                for food_name, amount in foods:
                    amount_in_grams = float(amount)
                    # Get the food's calories and protein from the database
                    self.cursor.execute(
                        'SELECT calories_per_100g, protein_per_100g FROM basic_food WHERE food_name = ? UNION SELECT calories_per_100g, protein_per_100g FROM composite_food WHERE food_name = ?', (food_name, food_name))
                    food_data = self.cursor.fetchone()
                    if food_data:
                        calories_per_100g, protein_per_100g = food_data
                        total_calories_in += (calories_per_100g * amount_in_grams) / 100
                        total_protein += (protein_per_100g * amount_in_grams) / 100

            # Calories Out calculation from exercises
            total_calories_out = 0
            if exercises:
                exercise_list = [tuple(item.split(',')) for item in exercises.split(';')]
                for exercise, calories in exercise_list:
                    total_calories_out += float(calories)

            # Calculate prior weight difference (current weight - previous day's weight)
            prior_diff = "N/A"
            if weight is not None and previous_weight is not None:
                prior_diff = f"{weight - previous_weight:.2f}"

            # Calculate goal weight difference (weight - goal)
            goal_diff = f"{weight - Goal:.2f}" if weight is not None else "N/A"

            # Prepare the row for the table
            table_data.append([date, f"{weight}" if weight is not None else "N/A",
                               f"{total_calories_in:.0f}", f"{total_calories_out:.0f}",
                               f"{total_protein:.0f}", prior_diff, goal_diff])

            # Update previous_weight for the next iteration (current row weight becomes previous_weight)
            previous_weight = weight

        # Reverse the list for display, so the most recent date is on top
        return table_data[::-1]

    def update_table(self):
        # Fetch the calculated table data
        table_data = self.calculate_daily_totals()

        # Update the table widget
        self.table.setRowCount(len(table_data))  # Adjust row count
        for row_idx, row_data in enumerate(table_data):
            try:
                # Extract weight from the row (column index 1 for weight)
                weight = float(row_data[1]) if row_data[1] != "N/A" else None

                # Extract protein intake, now it's just a number without "g" (column index 4 for protein)
                protein = float(row_data[4]) if row_data[4] != "N/A" else 0
            except ValueError:
                # Handle the case where weight or protein cannot be parsed correctly
                weight = None
                protein = 0

            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value))  # Create table item
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)  # Align text to center

                # Check if the current column is the 'Protein (g)' column and if weight is valid
                if col_idx == 4 and weight is not None:
                    # Check if protein intake is below 0.8 * weight
                    if protein < 0.8 * weight:
                        item.setForeground(QColor('red'))  # Set text color to red if condition is met
                    else:
                        item.setForeground(QColor('black'))  # Set text color back to default for valid values

                self.table.setItem(row_idx, col_idx, item)  # Add item to the table

        # Adjust rows and columns to fit the content
        self.table.resizeRowsToContents()
        self.table.resizeColumnsToContents()

        # Update the graph every time the table is updated
        self.update_graph()

    def add_composite_ingredient(self):
        # Create a new row with a dropdown and input field for additional ingredient
        new_dropdown = QComboBox()
        new_dropdown.setEditable(True)

        new_input = QLineEdit()

        # Add the new row to the composite layout
        new_row = QHBoxLayout()
        new_row.addWidget(new_dropdown)
        new_row.addWidget(new_input)

        # Add the new row just above the "Additional Ingredient" button
        self.composite_layout.insertLayout(self.composite_layout.count() - 1, new_row)
        self.new_food_dialog.adjustSize()  # Adjust size dynamically after adding rows

    def save_basic_food(self):
        # Get the values from the input fields
        food_name = self.input_1.text().strip()
        calories = self.input_2.text().strip()
        protein = self.input_3.text().strip()

        # Validate inputs are not empty
        if not food_name or not calories or not protein:
            return  # Do nothing if any field is empty

        # Insert the basic food into the database
        self.cursor.execute('''INSERT INTO basic_food (food_name, calories_per_100g, protein_per_100g)
                               VALUES (?, ?, ?)''', (food_name, float(calories), float(protein)))
        self.conn.commit()

        # Refresh dropdowns to show the newly added food
        self.refresh_food_dropdowns()

        # Close the dialog
        self.new_food_dialog.accept()

    def add_composite_ingredient_row(self):
        row_layout = QHBoxLayout()

        dropdown = QComboBox()
        dropdown.setEditable(True)  # Allow user to type/select a food
        self.populate_dropdown(dropdown, "food")  # Populate with basic/composite foods

        quantity_input = QLineEdit()

        row_layout.addWidget(dropdown)
        row_layout.addWidget(quantity_input)

        self.composite_ingredient_rows.append((dropdown, quantity_input))  # Store row

        # Add the new row to the ingredient rows layout
        self.ingredient_rows_layout.addLayout(row_layout)

    def save_composite_food(self):
        composite_name = self.input_1.text().strip()  # Composite food name
        if not composite_name:
            return  # Do nothing if name is empty

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
                self.cursor.execute('''SELECT calories_per_100g, protein_per_100g
                                       FROM basic_food WHERE food_name = ?
                                       UNION SELECT calories_per_100g, protein_per_100g
                                       FROM composite_food WHERE food_name = ?''',
                                    (ingredient_name, ingredient_name))
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

            # Save the composite food into the database
            ingredients_str = ';'.join([f"{name},{amount}" for name, amount in ingredients])
            self.cursor.execute('''INSERT INTO composite_food (food_name, ingredients, calories_per_100g, protein_per_100g)
                                   VALUES (?, ?, ?, ?)''',
                                (composite_name, ingredients_str, composite_calories_per_100g, composite_protein_per_100g))
            self.conn.commit()

        # Refresh dropdowns to show the newly added food
        self.refresh_food_dropdowns()

        # Close the dialog
        self.new_food_dialog.accept()

    def save_daily_data(self, date, weight, food_consumed, exercises):
        food_str = ';'.join([f"{name},{amount}" for name, amount in food_consumed])
        exercise_str = ';'.join([f"{name},{calories}" for name, calories in exercises])
        self.cursor.execute('''INSERT OR REPLACE INTO daily_data (date, weight, food_consumed, exercises)
                               VALUES (?, ?, ?, ?)''', (date, weight, food_str, exercise_str))
        self.conn.commit()

    def show_date_popup(self):
        # Create a QDialog for the date popup
        date_dialog = QDialog(self)
        date_dialog.setWindowTitle("Select Date")

        # Layout for the popup
        layout = QVBoxLayout()

        # Calendar widget to select a date
        self.calendar = QCalendarWidget()
        self.calendar.setSelectedDate(QDate.currentDate())  # Set default date to today's date

        layout.addWidget(self.calendar)

        # Buttons for Select and Cancel
        button_layout = QHBoxLayout()
        btn_select = QPushButton("Select")
        btn_cancel = QPushButton("Cancel")

        # Connect the buttons to actions
        btn_select.clicked.connect(lambda: self.select_date(date_dialog))
        btn_cancel.clicked.connect(date_dialog.reject)  # Close without selection

        button_layout.addWidget(btn_select)
        button_layout.addWidget(btn_cancel)

        # Add the buttons to the layout
        layout.addLayout(button_layout)

        # Set the layout for the dialog
        date_dialog.setLayout(layout)

        # Execute the dialog
        date_dialog.exec()

    def select_date(self, dialog):
        """Set the selected date from the calendar and highlight it in the table."""
        self.selected_date = self.calendar.selectedDate()  # Get the selected date
        self.highlight_selected_date()  # Highlight the row in the table
        dialog.accept()  # Close the dialog

    def create_table(self, layout):
        # Create table with dynamic rows and 7 fixed columns (as seen in your image)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ['Date', 'Weight (kg)', 'Calories In', 'Calories Out', 'Protein (g)', '\u0394 Prior (kg)', '\u0394 Goal (kg)'])

        # Make header bold
        font = self.table.horizontalHeader().font()
        font.setBold(True)
        self.table.horizontalHeader().setFont(font)

        # Enable alternating row colors
        self.table.setAlternatingRowColors(True)

        # Ensure columns expand to fit both headers and data
        self.table.horizontalHeader().setStretchLastSection(False)  # Stretch the last column to fill space
        self.table.resizeColumnsToContents()  # Adjusts all columns based on content and headers

        # Enable vertical scrollbar but no horizontal scrollbar
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Set the table to fill the available space and prevent horizontal gaps
        self.table.setSizeAdjustPolicy(QTableWidget.SizeAdjustPolicy.AdjustToContents)

        # Disable interaction (non-editable)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # Add the table to the layout with zero margins to prevent horizontal gap
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.table)

    def create_input_section(self, layout):
        # Input field 1 with Button 1, and space between Button 1 and Button 2
        field_label_1 = QLabel("Weight")
        layout.addWidget(field_label_1)
        input_layout_1 = QHBoxLayout()
        self.input_field_1 = QLineEdit()
        self.input_field_1.setFixedWidth(InputWidth)  # Make input field 1 shorter
        btn_1 = QPushButton("Add")
        btn_1.setFixedWidth(ButtonWidth)
        spacer = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)  # Space between buttons
        btn_2 = QPushButton("Settings")
        btn_2.setFixedWidth(ButtonWidth)
        btn_2.clicked.connect(self.show_settings_popup)  # Connect the button to open settings popup
        input_layout_1.addWidget(self.input_field_1)
        input_layout_1.addWidget(btn_1)
        input_layout_1.addSpacerItem(spacer)  # Space between Button 1 and Button 2
        input_layout_1.addWidget(btn_2)
        layout.addLayout(input_layout_1)
        btn_1.clicked.connect(self.save_weight)

        # Searchable Dropdown + Numerical Input Fields
        label_layout = QHBoxLayout()  # New horizontal layout for labels
        search_field_1_label = QLabel("Exercise")
        search_field_2_label = QLabel("Calories")
        spacer_middle = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        label_layout.addWidget(search_field_1_label)
        label_layout.addSpacerItem(spacer_middle)
        label_layout.addWidget(search_field_2_label)
        search_field_2_label.setFixedWidth(ButtonWidth + InputWidth + 5)
        layout.addLayout(label_layout)

        input_layout_2 = QHBoxLayout()
        self.dropdown_1 = QComboBox()
        self.dropdown_1.setEditable(True)
        self.populate_dropdown(self.dropdown_1, "exercise")  # Populate exercise dropdown
        self.dropdown_1.setCurrentIndex(-1)

        self.input_field_2 = QLineEdit()
        self.input_field_2.setFixedWidth(InputWidth)  # Make numerical input fields the same length
        btn_3 = QPushButton("Add")
        btn_3.setFixedWidth(ButtonWidth)
        btn_3.clicked.connect(self.save_exercise)

        input_layout_2.addWidget(self.dropdown_1)
        input_layout_2.addWidget(self.input_field_2)
        input_layout_2.addWidget(btn_3)
        layout.addLayout(input_layout_2)

        label_layout = QHBoxLayout()  # New horizontal layout for labels
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
        self.input_field_3.setFixedWidth(InputWidth)  # Make numerical input fields the same length
        btn_4 = QPushButton("Add")
        btn_4.setFixedWidth(ButtonWidth)
        btn_4.clicked.connect(self.save_food)

        input_layout_3.addWidget(self.dropdown_2)
        input_layout_3.addWidget(self.input_field_3)
        input_layout_3.addWidget(btn_4)
        layout.addLayout(input_layout_3)

        # Another Numerical Input Field with a Button, aligned to the right

        # Searchable Dropdown + Numerical Input Fields
        label_layout = QHBoxLayout()  # New horizontal layout for labels
        label_layout.addSpacerItem(spacer_middle)
        field_label_5 = QLabel("Calories")
        field_label_5.setFixedWidth(ButtonWidth + InputWidth + 5)
        label_layout.addWidget(field_label_5)
        layout.addLayout(label_layout)

        input_layout_4 = QHBoxLayout()
        spacer_left = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)  # Left gap
        self.input_field_4 = QLineEdit()
        self.input_field_4.setFixedWidth(InputWidth)  # Align this to the right
        btn_9 = QPushButton("New Food")
        btn_9.setFixedWidth(ButtonWidth)
        btn_9.clicked.connect(self.show_new_food_popup)  # Connect the new food button to open new food popup
        btn_5 = QPushButton("Calculate")
        btn_5.setFixedWidth(ButtonWidth)
        btn_5.clicked.connect(self.calculate_food_quantity)
        input_layout_4.addWidget(btn_9)
        input_layout_4.addSpacerItem(spacer_left)  # Add a spacer to the left
        input_layout_4.addWidget(self.input_field_4)
        input_layout_4.addWidget(btn_5)
        layout.addLayout(input_layout_4)

        # Three more buttons side by side
        btn_layout = QHBoxLayout()
        btn_6 = QPushButton("Previous Day")
        btn_7 = QPushButton("Date")
        btn_8 = QPushButton("Next Day")
        btn_layout.addWidget(btn_6)
        btn_layout.addWidget(btn_7)
        btn_7.clicked.connect(self.show_date_popup)  # Connect the date button to open date popup
        btn_layout.addWidget(btn_8)
        layout.addLayout(btn_layout)
        btn_6.clicked.connect(self.move_to_previous_day)  # Previous Day
        btn_8.clicked.connect(self.move_to_next_day)  # Next Day

    def create_graph(self):
        # Create the main plot widget
        self.graph_widget = pg.PlotWidget()

        # Create a custom x-axis with rotated labels
        custom_axis = CustomAxisItem(orientation='bottom')  # Custom x-axis with rotation
        self.graph_widget.plotItem.setAxisItems({'bottom': custom_axis})

        # Set background and labels
        self.graph_widget.setBackground('w')

        # Move the x-axis up by increasing the bottom padding
        self.graph_widget.plotItem.getViewBox().setContentsMargins(0, 0, 0, 50)  # Increase bottom padding for axis space

        # Set a fixed height for the bottom axis to create more space between the axis and the "Date" label
        custom_axis.setHeight(58)  # Adjust this value to create space between x-axis and label

        # Set the labels for axes
        self.graph_widget.plotItem.setLabel('left', 'Weight (kg)')
        self.graph_widget.plotItem.setLabel('bottom')  # No need for an offset here, space is controlled by axis

        # Add the right axis for calories
        self.graph_widget.plotItem.showAxis('right')
        self.graph_widget.plotItem.getAxis('right').setLabel('Calories (kcal)')

        return self.graph_widget

    def sync_right_y_axis(self):
        """Manually synchronize the right y-axis with the left y-axis but display actual calorie values."""
        left_range = self.graph_widget.plotItem.vb.viewRange()[1]  # Get the left y-axis range (weights)
        max_weight = left_range[1]  # Upper bound of the weight range

        # Check if max_calories and max_weight are greater than 0
        if self.max_calories > 0 and max_weight > 0:
            # Calculate the calorie range based on the normalization factor (a kg = b cal)
            normalization_factor = self.max_weight / self.max_calories

            # Update the ticks and labels for the right axis to show actual calorie values with increments of 100
            self.graph_widget.plotItem.getAxis('right').setTicks(
                [list(self._generate_right_axis_ticks(left_range, normalization_factor))]
            )

    def _generate_right_axis_ticks(self, left_range, normalization_factor):
        """Generate ticks for the right y-axis based on the left y-axis range and normalization factor."""
        left_min, left_max = left_range
        right_min = left_min / normalization_factor
        right_max = left_max / normalization_factor

        # Find the closest multiple of 100 to the min and max values for nice tick marks
        right_min = (int(right_min) // 100) * 100
        right_max = (int(right_max) // 100 + 1) * 100

        # Generate tick labels for the right axis at increments of 100
        right_ticks = []
        for right_value in range(int(right_min), int(right_max) + 1, 100):
            left_value = right_value * normalization_factor  # The corresponding left axis value
            right_ticks.append((left_value, f"{right_value}"))  # Display the right axis value without "cal"

        return right_ticks

    def update_graph(self):
        # Clear existing items in the graph
        for item in self.graph_widget.listDataItems():
            self.graph_widget.removeItem(item)

        # Fetch data from the table (dates, weights, calories in, calories out)
        dates = []
        weights = []
        calories_in = []
        calories_out = []

        # Loop through the table to extract data
        for row in range(self.table.rowCount()):
            date_item = self.table.item(row, 0)  # Date
            weight_item = self.table.item(row, 1)  # Weight
            calories_in_item = self.table.item(row, 2)  # Calories In
            calories_out_item = self.table.item(row, 3)  # Calories Out

            # Append data to lists
            if date_item and weight_item and calories_in_item and calories_out_item:
                dates.append(date_item.text())
                weights.append(float(weight_item.text()) if weight_item.text() != "N/A" else None)
                calories_in.append(float(calories_in_item.text()) if calories_in_item.text() != "N/A" else 0)
                calories_out.append(float(calories_out_item.text()) if calories_out_item.text() != "N/A" else 0)

        # Reverse data to make it descending (most recent first)
        dates.reverse()
        weights.reverse()
        calories_in.reverse()
        calories_out.reverse()

        # Create indices for the x-axis
        date_indices = list(range(len(dates)))

        # Find the maximum weight and calorie value for normalization
        self.max_weight = max([w for w in weights if w is not None]) if weights else 0
        self.max_calories = max(max(calories_in), max(calories_out)) if calories_in and calories_out else 0

        # Normalize calories based on max weight (a kg = b cal)
        normalization_factor = self.max_weight / self.max_calories if self.max_calories > 0 else 1

        # Normalize calories_in and calories_out for plotting but display actual calorie values on the right y-axis
        normalized_calories_in = [cal * normalization_factor for cal in calories_in]
        normalized_calories_out = [cal * normalization_factor for cal in calories_out]

        # Convert color names to QColor/RGBA tuples
        weight_color = get_color_from_name(self.weight_color, int(self.weight_opacity * 2.55))  # Opacity is 0-255
        calories_in_color = get_color_from_name(self.calories_in_color, int(self.calories_in_opacity * 2.55))
        calories_out_color = get_color_from_name(self.calories_out_color, int(self.calories_out_opacity * 2.55))

        # Plot the weight data on the left y-axis (main axis)
        weight_shape_symbol = get_shape_symbol(self.weight_shape)
        calories_in_shape_symbol = get_shape_symbol(self.calories_in_shape)
        calories_out_shape_symbol = get_shape_symbol(self.calories_out_shape)

        # Plot normalized calories in/out on the right y-axis (added first so they are beneath weight)
        calories_out_scatter = pg.ScatterPlotItem(
            size=self.calories_out_size,
            pen=pg.mkPen(color=calories_out_color),
            brush=pg.mkBrush(calories_out_color),
            symbol=calories_out_shape_symbol
        )
        calories_in_scatter = pg.ScatterPlotItem(
            size=self.calories_in_size,
            pen=pg.mkPen(color=calories_in_color),
            brush=pg.mkBrush(calories_in_color),
            symbol=calories_in_shape_symbol
        )

        # Add the calorie scatter plots first (to make them appear behind the weight)
        calories_out_scatter.setData(date_indices, normalized_calories_out)
        self.graph_widget.addItem(calories_out_scatter)

        calories_in_scatter.setData(date_indices, normalized_calories_in)
        self.graph_widget.addItem(calories_in_scatter)

        # Plot the weight data on top
        weight_scatter = pg.ScatterPlotItem(
            size=self.weight_size,
            pen=pg.mkPen(color=weight_color),
            brush=pg.mkBrush(weight_color),
            symbol=weight_shape_symbol
        )
        weight_scatter.setData(date_indices, weights)
        self.graph_widget.addItem(weight_scatter)

        # Update the graph widget and force repaint
        self.graph_widget.getViewBox().update()
        self.graph_widget.repaint()

        # Set x-axis labels and link to numeric indices of dates
        self.graph_widget.getAxis('bottom').setTicks([list(enumerate(dates))])

        # Set y-axis ranges with some padding (10% extra space)
        self.graph_widget.getViewBox().setYRange(0, self.max_weight * 1.1, padding=0)

        # Set the x-axis range for both views to ensure they align
        self.graph_widget.setXRange(0, len(dates) - 1)

        # Disable panning/zooming beyond the limits
        self.graph_widget.getViewBox().setLimits(xMin=0, xMax=len(dates) - 1, yMin=0, yMax=self.max_weight * 1.1)

        # Sync the right y-axis range to the left y-axis
        self.sync_right_y_axis()

    def update_table_from_database(self, data):
        """Method to update the table with data from a database"""
        self.table.setRowCount(len(data))  # Set the number of rows based on data
        for row_idx, row_data in enumerate(data):
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value))  # Create the item
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)  # Center-align the text
                self.table.setItem(row_idx, col_idx, item)  # Add the item to the table

        # Ensure the rows fit the data and can scroll vertically
        self.table.resizeRowsToContents()
        self.table.resizeColumnsToContents()  # Ensure columns resize for new data as well
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()

    app.setWindowIcon(QIcon("icon.ico"))
    # This will automatically load and update the table from the database
    window.show()
    sys.exit(app.exec())
