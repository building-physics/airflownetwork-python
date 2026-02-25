# SPDX-FileCopyrightText: 2023-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause
from platform import system
from sys import platform
from tkinter import Tk, PhotoImage, LabelFrame, Entry, StringVar, Menu, DISABLED, Frame, Label, NSEW, E, VERTICAL, \
    SUNKEN, S, LEFT, BOTH, messagebox, END, BooleanVar, NORMAL, RIGHT, EW, NS, filedialog, \
    ALL, Scrollbar, SINGLE, Variable, HORIZONTAL
from tkinter.ttk import Frame, LabelFrame, Checkbutton, Combobox, PanedWindow as ttkPanedWindow, OptionMenu, Notebook
if system() == 'Darwin':
    from tkmacosx import Button # type: ignore
else:
    from tkinter.ttk import Button
from pathlib import Path
from .__about__ import __version__
import importlib.resources

class AirflowNetworkUtilities(Tk):

    def name(self):
        return 'AirflowNetworkUtilities'

    def __init__(self, called_from_ep_cli:bool=False, title:str='AirflowNetwork Utilities',
                 min_width:int=1000, min_height:int=500):
        super().__init__(className=self.name())
        self.title(title)
        if called_from_ep_cli:
            self.option_add('*Dialog.msg.font', 'Helvetica 12')
        # Load the icon
        if system() == 'Windows':
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"{self.name()}.{__version__}")
            with importlib.resources.path('airflownetwork.data', 'eplus.ico') as icon_path:
                if icon_path.exists():
                    self.iconbitmap(icon_path)
                else:
                    print(f"Could not set icon, expecting to find it at {icon_path}")
        else:
            icon_file_name = 'eplus256.png'
            if system() == 'Darwin':
                icon_file_name = 'ep.icns'
            with importlib.resources.path('airflownetwork.data', icon_file_name) as icon_path:
                if icon_path.exists():
                    img = PhotoImage(file=str(icon_path))
                    self.iconphoto(False, img)
                else:
                    print(f"Could not set icon, expecting to find it at {icon_path}")
        self.pad = {'padx': 3, 'pady': 3}

        self.gui()

        # set the minimum size and redraw the app
        #self.minsize(min_width, min_height)
        self.update()

        # one time update of the status bar
        #self._update_status_bar("Program Initialized")

        # potentially show a welcome screen if we are on a new version
        #self._open_welcome()

        # Bind keys and focus events
        #self.bind('<Key>', self.handle_keypress)
        #self.bind("<FocusIn>", self.handle_focus_in)

    def handle_keypress(self, event) -> None:
        pass

    def handle_focus_in(self, _event) -> None:
        pass

    def gui(self):
        self.file_entry_chars = 80
        self.top_menu()

        nb = Notebook(self)

        # Set up the auditor
        self.auditor = Frame(nb, padding=(3, 3, 12, 12))
        self.auditor.grid(column=0, row=0, sticky=NSEW)
        
        # Set up the iternal frames
        self.auditor_input = self.file_entry(self.auditor)
        self.auditor_settings_input(self.auditor)

        

        # Set up the generator
        self.generator = Frame(nb, padding=(3, 3, 12, 12))
        self.generator.grid(column=0, row=0, sticky=NSEW)
        
        self.generator_input, self.generator_output = self.file_entry(self.generator, output=True)
        self.generator_settings_input(self.generator)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.auditor.columnconfigure(0, weight=1)
        self.auditor.rowconfigure(1, weight=1)
        self.generator.columnconfigure(0, weight=1)
        self.generator.rowconfigure(1, weight=1)

        #height = 500
        #width = 1000
        #x = 128
        #y = 128

        # Initial coordination between the various parts
        self.update_add_objects()
        #self.update_save_intermediates()

        nb.add(self.auditor, text='Network Auditor')
        nb.add(self.generator, text='Network Generator')
        nb.pack(expand=1, fill="both")

        #self.wm_geometry(f"{width}x{height}+{x}+{y}")

    def top_menu(self):
        menubar = Menu(self)

        # File menu
        menu = Menu(menubar, tearoff=False)
        #menu.add_separator()
        menu.add_command(label="Quit", command=self.window_close)
        menubar.add_cascade(label="File", menu=menu)

        # Help menu
        menu = Menu(menubar, tearoff=False)
        #menu.add_command(label="Documentation...", command=self.open_documentation)
        menu.add_command(label="About...", command=self.about_dialog)
        menubar.add_cascade(label="Help", menu=menu)

        self.config(menu=menubar)

    def file_entry(self, parent, output=False):
        files = LabelFrame(parent, text='Files')
        files.grid(column=0, row=0, sticky=NSEW)

        Label(files, text='IDF/epJSON').grid(column=0, row=0, sticky=EW)
        input_file = Entry(files, width=self.file_entry_chars)
        input_file.grid(column=1, row=0, sticky=EW)
        Button(files, text='Browse').grid(column=2, row=0, sticky=EW)

        if output:
            #Label(files, text='View3D Output').grid(column=0, row=1, sticky=EW)
            #self.output_file = Entry(files, width=self.file_entry_chars)
            #self.output_file.grid(column=1, row=1, sticky=EW)
            #Button(files, text='Browse').grid(column=2, row=1, sticky=EW)

            Label(files, text='epJSON Output').grid(column=0, row=2, sticky=EW)
            output_file = Entry(files, width=self.file_entry_chars)
            output_file.grid(column=1, row=2, sticky=EW)
            Button(files, text='Browse').grid(column=2, row=2, sticky=EW)

            files.columnconfigure(1, weight=1)
            return input_file, output_file

        files.columnconfigure(1, weight=1)
        return input_file
    
    def auditor_settings_input(self, parent):
        settings = LabelFrame(parent, text='Settings')
        settings.grid(column=0, row=1, sticky=NSEW)

        self.include_distribution = BooleanVar()
        self.include_distribution.set(False)
        Checkbutton(settings, text='Include distribution', variable=self.include_distribution).grid(column=0, row=0, sticky=EW)

        #self.create_objects = BooleanVar()
        #self.create_objects.set(False)
        #Checkbutton(settings, text='Create EnergyPlus objects', variable=self.create_objects,
        #            command=self.update_create_objects).grid(column=0, row=1, sticky=EW)
        #
        #self.add_objects = BooleanVar()
        #self.add_objects.set(False)
        #Checkbutton(settings, text='Add EnergyPlus objects to IDF/epJSON', variable=self.add_objects).grid(column=0, row=2, sticky=EW)

        #self.save_intermediates = BooleanVar()
        #self.save_intermediates.set(True)
        #Checkbutton(settings, text='Save intermediate results', variable=self.save_intermediates,
        #            command=self.update_save_intermediates).grid(column=0, row=3, sticky=EW)

        settings.columnconfigure(0, weight=1)

    def generator_settings_input(self, parent, row=1):
        settings = LabelFrame(parent, text='Settings')
        settings.grid(column=0, row=row, sticky=NSEW)

        self.generate_distribution = BooleanVar()
        self.generate_distribution.set(False)
        Checkbutton(settings, text='Generate distribution', variable=self.generate_distribution).grid(column=0, row=0, sticky=EW)

        #self.create_objects = BooleanVar()
        #self.create_objects.set(False)
        #Checkbutton(settings, text='Create EnergyPlus objects', variable=self.create_objects,
        #            command=self.update_create_objects).grid(column=0, row=1, sticky=EW)
        #
        self.add_objects = BooleanVar()
        self.add_objects.set(False)
        Checkbutton(settings, text='Overwrite original epJSON', variable=self.add_objects,
                    command=self.update_add_objects).grid(column=0, row=2, sticky=EW)

        #self.save_intermediates = BooleanVar()
        #self.save_intermediates.set(True)
        #Checkbutton(settings, text='Save intermediate results', variable=self.save_intermediates,
        #            command=self.update_save_intermediates).grid(column=0, row=3, sticky=EW)

        settings.columnconfigure(0, weight=1)

    def update_create_objects(self):
        if not self.create_objects.get():
            self.object_output_file.config(state='disabled')
        else:
            if self.save_intermediates.get():
                self.object_output_file.config(state='normal')

    def update_save_intermediates(self):
        if not self.save_intermediates.get():
            self.output_file.config(state='disabled')
            self.object_output_file.config(state='disabled')
        else:
            self.output_file.config(state='normal')

    def update_add_objects(self):
        if not self.add_objects.get():
            self.generator_output.config(state='normal')
        else:
            self.generator_output.config(state='disabled')

    def about_dialog(self):
        messagebox.showinfo('About', message = f'This is the {self.title()}, version {__version__}.')

    def run(self):
        self.protocol('WM_DELETE_WINDOW', self.window_close)
        self.mainloop()

    def window_close(self, *_):
        self.destroy()