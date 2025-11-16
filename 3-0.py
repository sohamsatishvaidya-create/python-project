# rock_paper_scissors_gui_threadsafe.py
# Copy-paste and run with: python rock_paper_scissors_gui_threadsafe.py
#
# Features:
# - Start / End buttons (Start truly starts the game)
# - Countdown before each round (3 -> 2 -> 1 -> GO)
# - Both player and computer animate and reveal at the same time
# - Thread-safe GUI updates using root.after(...)
# - Buttons disabled while a round is in progress
#
import tkinter as tk
from tkinter import messagebox
import threading
import random
import time

# ---------------------------
# Configuration / Globals
# ---------------------------
ICON_MAP = {"rock": "✊", "paper": "✋", "scissors": "✌️"}
CHOICES = ["rock", "paper", "scissors"]

# Game state
game_running = False         # True after Start pressed, false after End pressed
round_in_progress = False    # True while countdown/animation/result showing
user_score = 0
computer_score = 0

# Lock for thread-safety of state variables (simple safety)
state_lock = threading.Lock()

# ---------------------------
# Helper functions that update UI via root.after (thread-safe)
# ---------------------------
def set_label_text_safe(widget, text):
    """Schedule label.config(text=...) on the main thread."""
    widget.after(0, lambda: widget.config(text=text))

def set_label_fg_safe(widget, color):
    widget.after(0, lambda: widget.config(fg=color))

def enable_widget_safe(widget):
    widget.after(0, lambda: widget.config(state="normal"))

def disable_widget_safe(widget):
    widget.after(0, lambda: widget.config(state="disabled"))

# ---------------------------
# Core game worker (runs in background thread)
# ---------------------------
def round_worker(user_choice):
    global user_score, computer_score, round_in_progress, game_running

    # Quick guard: only proceed if game is running and no round currently in progress
    with state_lock:
        if not game_running or round_in_progress:
            return
        round_in_progress = True

    # Disable choice buttons while round runs (schedule on main thread)
    disable_widget_safe(rock_btn)
    disable_widget_safe(paper_btn)
    disable_widget_safe(scissors_btn)

    # --------------- Countdown ---------------
    countdown_values = ["3", "2", "1", "GO!"]
    for val in countdown_values:
        # If End was pressed during countdown, abort
        with state_lock:
            if not game_running:
                round_in_progress = False
                set_label_text_safe(countdown_label, "")
                enable_widget_safe(start_btn)
                return

        # show countdown number
        set_label_text_safe(countdown_label, f"{val}")
        # small color pulse for countdown
        set_label_fg_safe(countdown_label, "#FFA500")
        time.sleep(0.8)  # sleep off the main thread

    # clear countdown text
    set_label_text_safe(countdown_label, "")

    # --------------- Animation (both hands move together) ---------------
    # Choose computer's final choice
    computer_choice = random.choice(CHOICES)

    # Run small animation cycles (both sides cycle icons) and then stop on final icons
    cycles = 6
    for i in range(cycles):
        # pick random icons for the animation frame
        user_anim_icon = random.choice(list(ICON_MAP.values()))
        comp_anim_icon = random.choice(list(ICON_MAP.values()))
        set_label_text_safe(player_icon_label, user_anim_icon)
        set_label_text_safe(computer_icon_label, comp_anim_icon)
        time.sleep(0.12)

        # If game was ended mid-animation, stop gracefully
        with state_lock:
            if not game_running:
                round_in_progress = False
                set_label_text_safe(countdown_label, "")
                enable_widget_safe(start_btn)
                return

    # Final reveal (both at same time)
    set_label_text_safe(player_icon_label, ICON_MAP[user_choice])
    set_label_text_safe(computer_icon_label, ICON_MAP[computer_choice])

    # --------------- Determine result ---------------
    if user_choice == computer_choice:
        result_text = "It's a Tie!"
    elif (user_choice == "rock" and computer_choice == "scissors") or \
         (user_choice == "paper" and computer_choice == "rock") or \
         (user_choice == "scissors" and computer_choice == "paper"):
        result_text = "You Win this round!"
        with state_lock:
            user_score += 1
    else:
        result_text = "Computer Wins this round!"
        with state_lock:
            computer_score += 1

    # Update scores and result on UI
    set_label_text_safe(result_label, result_text)
    set_label_text_safe(score_label, f"🏆 You: {user_score}   💻 Computer: {computer_score}")

    # short pause for user to see result
    time.sleep(1.0)

    # Re-enable choice buttons only if game still running
    with state_lock:
        round_in_progress = False
        still_running = game_running

    if still_running:
        enable_widget_safe(rock_btn)
        enable_widget_safe(paper_btn)
        enable_widget_safe(scissors_btn)
    else:
        # If game ended meanwhile, ensure Start is enabled
        enable_widget_safe(start_btn)

# ---------------------------
# Button callbacks (main thread)
# ---------------------------
def on_start():
    global game_running, user_score, computer_score
    with state_lock:
        game_running = True
        user_score = 0
        computer_score = 0

    # reset UI
    score_label.config(text=f"🏆 You: {user_score}   💻 Computer: {computer_score}")
    result_label.config(text="Game started! Make your move.")
    set_label_text_safe(player_icon_label, "❔")
    set_label_text_safe(computer_icon_label, "❔")
    set_label_text_safe(countdown_label, "")

    # enable choices and disable start button
    rock_btn.config(state="normal")
    paper_btn.config(state="normal")
    scissors_btn.config(state="normal")
    start_btn.config(state="disabled")
    end_btn.config(state="normal")

def on_end():
    global game_running
    with state_lock:
        game_running = False

    # disable choice buttons, show final scores message
    rock_btn.config(state="disabled")
    paper_btn.config(state="disabled")
    scissors_btn.config(state="disabled")
    start_btn.config(state="normal")
    end_btn.config(state="disabled")

    messagebox.showinfo("Game Over", f"Final Scores:\nYou: {user_score}\nComputer: {computer_score}")
    result_label.config(text="Game ended. Press Start to play again.")

def on_choice(choice):
    # Called when user clicks a choice button (main thread) — spawn worker thread
    with state_lock:
        if not game_running:
            result_label.config(text="⚠️ Press Start to begin the game.")
            return
        if round_in_progress:
            result_label.config(text="⚠️ Wait for current round to finish.")
            return

    # Show selected choice immediately on player's icon - but animation will override then reveal
    player_icon_label.config(text=ICON_MAP[choice])
    result_label.config(text="Round starting...")

    # Start background worker for countdown + animation + result
    worker_thread = threading.Thread(target=round_worker, args=(choice,), daemon=True)
    worker_thread.start()

# ---------------------------
# Build GUI
# ---------------------------
root = tk.Tk()
root.title("Rock Paper Scissors — Simultaneous Reveal")
root.geometry("760x640")
root.config(bg="#101820")

# Title
title = tk.Label(root, text="🎮 Rock - Paper - Scissors", font=("Comic Sans MS", 26, "bold"), fg="#FEE715", bg="#101820")
title.pack(pady=12)

# Score
score_label = tk.Label(root, text=f"🏆 You: {user_score}   💻 Computer: {computer_score}", font=("Arial", 16, "bold"), fg="white", bg="#101820")
score_label.pack(pady=6)

# Main animation area (player vs computer)
animation_frame = tk.Frame(root, bg="#101820")
animation_frame.pack(pady=18)

player_frame = tk.Frame(animation_frame, bg="#101820")
player_frame.grid(row=0, column=0, padx=80)

vs_label = tk.Label(animation_frame, text="VS", font=("Arial", 28, "bold"), fg="yellow", bg="#101820")
vs_label.grid(row=0, column=1)

computer_frame = tk.Frame(animation_frame, bg="#101820")
computer_frame.grid(row=0, column=2, padx=80)

player_label = tk.Label(player_frame, text="You", font=("Arial", 16, "bold"), fg="#FEE715", bg="#101820")
player_label.pack()
player_icon_label = tk.Label(player_frame, text="❔", font=("Arial", 86), fg="lime", bg="#101820")
player_icon_label.pack()

computer_label = tk.Label(computer_frame, text="Computer", font=("Arial", 16, "bold"), fg="#FEE715", bg="#101820")
computer_label.pack()
computer_icon_label = tk.Label(computer_frame, text="❔", font=("Arial", 86), fg="red", bg="#101820")
computer_icon_label.pack()

# Countdown label
countdown_label = tk.Label(root, text="", font=("Arial", 36, "bold"), fg="orange", bg="#101820")
countdown_label.pack(pady=8)

# Result label
result_label = tk.Label(root, text="Press Start to begin", font=("Arial", 18, "bold"), fg="white", bg="#101820")
result_label.pack(pady=10)

# Choice buttons
choice_frame = tk.Frame(root, bg="#101820")
choice_frame.pack(pady=12)

rock_btn = tk.Button(choice_frame, text="✊ Rock", font=("Arial", 14, "bold"), width=12, bg="#3366ff", fg="white", command=lambda: on_choice("rock"))
rock_btn.grid(row=0, column=0, padx=12)

paper_btn = tk.Button(choice_frame, text="✋ Paper", font=("Arial", 14, "bold"), width=12, bg="#33cc33", fg="white", command=lambda: on_choice("paper"))
paper_btn.grid(row=0, column=1, padx=12)

scissors_btn = tk.Button(choice_frame, text="✌️ Scissors", font=("Arial", 14, "bold"), width=12, bg="#ff3333", fg="white", command=lambda: on_choice("scissors"))
scissors_btn.grid(row=0, column=2, padx=12)

# Control buttons (Start / End)
control_frame = tk.Frame(root, bg="#101820")
control_frame.pack(pady=18)

start_btn = tk.Button(control_frame, text="▶ Start Game", font=("Arial", 14, "bold"), width=16, bg="#00cc99", fg="white", command=on_start)
start_btn.grid(row=0, column=0, padx=10)

end_btn = tk.Button(control_frame, text="⏹ End Game", font=("Arial", 14, "bold"), width=16, bg="#ff6666", fg="white", state="disabled", command=on_end)
end_btn.grid(row=0, column=1, padx=10)

# Footer
footer = tk.Label(root, text="Created by Yash Bhor | Python Project", font=("Arial", 10), fg="gray", bg="#101820")
footer.pack(side="bottom", pady=10)

# Disable choice buttons until Start pressed
rock_btn.config(state="disabled")
paper_btn.config(state="disabled")
scissors_btn.config(state="disabled")

# Start Tkinter event loop
root.mainloop()
