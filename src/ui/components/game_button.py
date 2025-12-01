import tkinter as tk

class GameButton3D(tk.Canvas):
    """
    Canvas-based button simulating a 3D "pushable" game button.
    Draws rounded rectangles for face and depth.
    """
    def __init__(self, parent, text, subtext=None, 
                 face_color="#333333", depth_color="#111111", 
                 width=180, height=65, corner_radius=15, 
                 command=None, state="normal"):
        super().__init__(parent, width=width, height=height, bg=parent["bg"], highlightthickness=0, cursor="hand2")
        self.command = command
        self.state_val = state  # "normal" or "disabled"
        
        self.face_color = face_color
        self.depth_color = depth_color
        self.text = text
        self.subtext = subtext
        self.corner_radius = corner_radius
        
        self.width = width
        self.height = height
        self.depth = 8  # Height of the "3D" part
        
        self.pressed = False
        
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Enter>", self._on_hover)
        self.bind("<Leave>", self._on_leave)
        
        self.draw()

    def config(self, **kwargs):
        """Mimic standard widget config behavior"""
        if 'state' in kwargs:
            self.state_val = kwargs.pop('state')
            if self.state_val == "disabled":
                self.configure(cursor="arrow")
            else:
                self.configure(cursor="hand2")
            self.draw()
        
        # Pass other kwargs to super
        if kwargs:
            super().configure(**kwargs)

    def round_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [x1+radius, y1,
                  x1+radius, y1,
                  x2-radius, y1,
                  x2-radius, y1,
                  x2, y1,
                  x2, y1+radius,
                  x2, y1+radius,
                  x2, y2-radius,
                  x2, y2-radius,
                  x2, y2,
                  x2-radius, y2,
                  x2-radius, y2,
                  x1+radius, y2,
                  x1+radius, y2,
                  x1, y2,
                  x1, y2-radius,
                  x1, y2-radius,
                  x1, y1+radius,
                  x1, y1+radius,
                  x1, y1]
        return self.create_polygon(points, **kwargs, smooth=True)

    def draw(self):
        self.delete("all")
        
        w, h = self.width, self.height
        d = self.depth
        r = self.corner_radius
        
        # Disabled state: Grayed out
        if self.state_val == "disabled":
            face = "#555555"
            depth = "#333333"
            offset = d # Appear "pressed" or flat? Let's keep it unpressed but gray
            offset = 0
        else:
            face = self.face_color
            depth = self.depth_color
            offset = d if self.pressed else 0
        
        # 1. Draw Depth Layer (The "Shadow" or "Side")
        if not self.pressed or self.state_val == "disabled":
            self.round_rect(2, h-d-2, w-2, h-2, r, fill=depth)
            # Connect the gap if needed
            self.create_rectangle(2, h/2, w-2, h-r, fill=depth, outline="")

        # 2. Draw Face Layer
        face_y1 = 2 + offset
        face_y2 = h - d - 2 + offset
        
        self.round_rect(2, face_y1, w-2, face_y2, r, fill=face)
        
        # 3. Text
        face_center_y = (face_y1 + face_y2) / 2
        
        text_color = "white"
        if self.state_val == "disabled":
            text_color = "#aaaaaa"

        if self.subtext:
            self.create_text(w/2, face_center_y - 9, text=self.text, fill=text_color, font=("Comic Sans MS", 16, "bold"))
            self.create_text(w/2, face_center_y + 11, text=self.subtext, fill=text_color, font=("Arial", 9, "bold"))
        else:
            self.create_text(w/2, face_center_y, text=self.text, fill=text_color, font=("Comic Sans MS", 16, "bold"))

    def _on_press(self, event):
        if self.state_val == "disabled": return
        self.pressed = True
        self.draw()

    def _on_release(self, event):
        if self.state_val == "disabled": return
        self.pressed = False
        self.draw()
        if self.command:
            self.command()
            
    def _on_hover(self, event):
        if self.state_val == "disabled": return
        # Optional hover effect (e.g. lighten)
        pass

    def _on_leave(self, event):
        if self.state_val == "disabled": return
        self.pressed = False
        self.draw()
