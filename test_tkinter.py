#!/usr/bin/env python3
import tkinter as tk

root = tk.Tk()
root.title("Color Test")
root.geometry("400x400")
root.configure(bg='white')

# Test 1: Label with explicit colors
label1 = tk.Label(root, text="Test 1: Can you see this?",
                  font=("Arial", 16),
                  bg='yellow',
                  fg='black')
label1.pack(pady=10)

# Test 2: Label with different colors
label2 = tk.Label(root, text="Test 2: Different colors",
                  font=("Helvetica", 14),
                  bg='lightblue',
                  fg='red')
label2.pack(pady=10)

# Test 3: Button (this works for you)
button = tk.Button(root, text="Button (you can see this)",
                   bg='green',
                   fg='white')
button.pack(pady=10)

# Test 4: Entry with colors
entry = tk.Entry(root, width=30,
                 bg='lightgray',
                 fg='black',
                 font=("Arial", 12))
entry.pack(pady=10)
entry.insert(0, "Entry field test")

# Test 5: Text widget
text = tk.Text(root, width=30, height=3,
               bg='lightyellow',
               fg='black',
               font=("Arial", 12))
text.pack(pady=10)
text.insert('1.0', "Text widget test\nCan you see this?")

root.mainloop()
