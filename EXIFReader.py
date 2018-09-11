import Tkinter as tk
import tkFileDialog
import ttk
from PIL import Image, ImageTk
import piexif
import warnings

# the piexif module throws a UnicodeWarning when opening a second picture
# it should be a bug in piexif itself, but the program still works so the warning can be ignored
warnings.simplefilter("ignore", UnicodeWarning)


class App(tk.Tk):

    def __init__(self, *args, **kwargs):

        tk.Tk.__init__(self, *args, **kwargs)

        # *****INITIAL WINDOW SETUP*****

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        tk.Tk.wm_title(self, "EXIF Reader")

        self.geometry("350x650+0+0")

        # make a container frame containing the ReadPage
        # idea is that the code will be scalable if more windows/frames will be needed
        self.container = DataPage(self)
        self.container.grid(row=0, column=0, sticky="nesw")

        # *****MENU*****

        menu = tk.Menu(self)

        fileMenu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="File", menu=fileMenu)
        fileMenu.add_command(label="Open", command=self.container.OpenFile)
        fileMenu.add_command(label="Close", command=self.container.CloseFile)
        fileMenu.add_separator()
        fileMenu.add_command(label="Exit", command=self.quit)

        self.config(menu=menu)


class DataPage(tk.Frame):

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        self.grid_rowconfigure(0, weight=1, uniform='a')
        self.grid_rowconfigure(1, weight=3, uniform='a')
        self.grid_rowconfigure(2, weight=9, uniform='a')

        self.grid_columnconfigure(0, weight=20, uniform='b')
        self.grid_columnconfigure(1, weight=1, uniform='b')

        # *****Header Frame*****

        self.FrameHeader = tk.Frame(master=self)
        self.FrameHeader.grid(row=0, column=0, columnspan=2, sticky="nesw")

        self.LabelName = tk.Label(master=self.FrameHeader, text="No File Open", font=("Verdana", 14))
        self.LabelName.place(relx=.5, rely=.5, anchor=tk.CENTER)


        # *****Picture Frame*****

        self.FramePic = tk.Frame(master=self, borderwidth=2, relief=tk.FLAT, bg="gray")
        self.FramePic.grid(row=1, column=0, columnspan=2, sticky="nesw")

        # declaring these in __init__, used in AddPicture and ResizePicture
        self.img = None
        self.Tkimg = None

        self.LabelPic = tk.Label(master=self.FramePic, borderwidth=0)
        self.LabelPic.pack()

        self.FramePic.bind("<Configure>", self.OnFramePicConfigure)


        # *****Text/Data Frame*****

        self.CanvasText = tk.Canvas(self)
        self.CanvasText.grid(row=2, column=0, sticky="nesw")

        self.scrollbar = ttk.Scrollbar(self, command=self.CanvasText.yview)
        self.scrollbar.grid(row=2, column=1, sticky="nes")

        self.CanvasText.configure(yscrollcommand=self.scrollbar.set)

        self.FrameText = tk.Frame(master=self.CanvasText)

        # keys
        self.FrameText.grid_columnconfigure(0, weight=1)
        # values
        self.FrameText.grid_columnconfigure(1, weight=1)

        # self.AddData(IMGPATH)

        self.CanvasText.create_window((0, 0), window=self.FrameText, anchor="nw", tags="frame")
        self.CanvasText.config(scrollregion=self.CanvasText.bbox(tk.ALL))

        self.FrameText.bind('<Configure>', self.OnFrameTextConfigure)
        self.CanvasText.bind('<Configure>', self.CanvasWidth)
        self.CanvasText.bind_all('<MouseWheel>', self.OnMouseWheel)

    def AddPicture(self, ImagePath):
        self.img = Image.open(ImagePath)

        # used for resizing
        # ImageTk version of the image
        self.Tkimg = ImageTk.PhotoImage(self.img)

        self.LabelPic.configure(image=self.Tkimg)
        # to keep a reference, otherwise the garbage collector ruins things
        self.LabelPic.image = self.Tkimg

        self.ResizePicture(self.FramePic.winfo_height(), self.FramePic.winfo_width())

    def AddData(self, ImagePath):
        # purge old data
        for widget in self.FrameText.winfo_children():
            widget.destroy()

        # get the data
        exif_dict = GetExifData(ImagePath)
        # sort alphabetically
        keylist = exif_dict.keys()
        keylist.sort()

        # set data in frame
        for i in range(len(keylist)):
            # keys
            label = tk.Label(master=self.FrameText, text=keylist[i] + ' :')
            label.grid(row=i, column=0, pady=5, sticky="e", )

            # values
            label = tk.Label(master=self.FrameText, text=exif_dict[keylist[i]])
            label.grid(row=i, column=1, pady=5, padx=20, sticky="w")

        # in case there is no data
        if not exif_dict:
            label = tk.Label(master=self.FrameText, text="No Metadata Found :(")
            label.grid(row=1, column=0, pady=5, sticky="e")

    # when the picture size is resized, resize the picture
    def OnFramePicConfigure(self, event):
        frameheight = event.height
        framewidth = event.width
        self.ResizePicture(frameheight, framewidth)

    # resize the picture while keeping the aspect ratio intact
    def ResizePicture(self, frameheight, framewidth):
        if not self.img:
            return
        aspectratio = self.img.size[0] / float(self.img.size[1])
        if framewidth/float(frameheight) > aspectratio:
            self.Tkimg = ImageTk.PhotoImage(self.img.resize((int(frameheight*aspectratio), frameheight), Image.ANTIALIAS))
        else:
            self.Tkimg = ImageTk.PhotoImage(self.img.resize((framewidth, int(framewidth/aspectratio)), Image.ANTIALIAS))
        self.LabelPic.configure(image=self.Tkimg)

    # when CanvasText (=window) is resized, stretch the FrameText to fill the canvas
    def CanvasWidth(self, event):
        canvaswidth = event.width
        self.CanvasText.itemconfig("frame", width=canvaswidth)

    # when FrameText size changes, update bbox
    def OnFrameTextConfigure(self, event):
        self.CanvasText.configure(scrollregion=self.CanvasText.bbox(tk.ALL))

    # scroll the scrollbar when mousewheel is used
    def OnMouseWheel(self, event):
        self.CanvasText.yview_scroll(-1*(event.delta/120), "units")

    # open a new image
    def OpenFile(self):
        filepath = tkFileDialog.askopenfilename(filetypes=[('JPEG image files', ('.jpg', '.jpeg'))])
        # if the user chose an image
        if filepath:
            # get the name of the file from the path
            LastSlash = filepath.rindex("/")
            filename = filepath[LastSlash+1:]

            self.LabelName.configure(text=filename)
            self.AddPicture(filepath)
            self.AddData(filepath)

    # close the currently open image
    def CloseFile(self):
        # change the image name
        self.LabelName.configure(text="No File Open")

        # purge old data
        for widget in self.FrameText.winfo_children():
            widget.destroy()

        # delete the image
        self.LabelPic.configure(image='')
        self.LabelPic.image = None


# Loads the exif data from the image and returns a dictionary with readable labels
def GetExifData(ImagePath):
    exif_dict = piexif.load(ImagePath)
    sorteddict = {}

    for ifd in ("0th", "Exif", "GPS", "1st"):
        for tag in exif_dict[ifd]:
            sorteddict[piexif.TAGS[ifd][tag]["name"]] = exif_dict[ifd][tag]

    return sorteddict

# main
if __name__ == "__main__":
    app = App()
    app.mainloop()
