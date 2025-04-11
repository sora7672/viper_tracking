# Viper Tracking

**Viper Tracking** is a local-first, privacy-focused desktop activity tracking tool designed 
for deep self-analysis, productivity evaluation, and time auditing. 
Built with performance-by-design and full user customizability in mind, 
it gives you full control over what is tracked, how it's labeled, 
and how it's analyzed - without compromising your data privacy.

---

## Table of Contents

- [Why should I use ViperTracking instead of XYZ?](#why-should-i-use-viper-tracking-instead-of-xyz?)
- [Roadmap](#roadmap)
- [Key Features](#key-features)
- [Design Philosophy](#design-philosophy)
- [Architecture & Technologies](#architecture--technologies)
- [Use Cases](#use-cases)
- [Installation](#installation)
- [Privacy & Security](#privacy--security)
- [License & Contribution](#license--contribution)
- [Why I Built This](#why-i-built-this)
- [Devlog](#devlog)
- [Contact](#contact)

---

## Why should I use ViperTracking instead of XYZ?

Simple. You are in full control of everything that happens here.  
I built this with intention and love. "Working" is never good enough for me.  
I keep improving it, so we can better understand how we spend our time and learn from it.

Whether it's projects, tickets, or just your daily screen routine,  
Viper Tracking helps you track it all in a way that works for you.

---

## Roadmap

This tool is not yet available as a *ready-to-run* installer.  
But don't worry  everything is coming together quickly.

Check out the [ViperTracking Roadmap](./docs/roadmap.md)  
to see what's already built, what's being worked on right now,  
and what's coming next.

---

## Key Features

- Track window focus and user input in 5-second intervals
- Fully offline and privacy-preserving - no external communication, no webinterface
- Dynamic labeling system (manual or conditional by AND/OR logic)
- Modular GUI built with ttkbootstrap and custom widgets
- Interactive GUI to create filters for timeframes with unlimited add/subtract logic
- Dynamic visualizations showing activity levels, app usage over time, extra app-based and label-based timelines. 
All fully interactive and filterable
- Auto-aggregation of low-percentage data in charts
- Multi-threaded architecture: input tracking, system tray, DB access and GUI
- System tray controls for quick label entry and GUI launch
- Keyboard-friendly UX with clean theming, custom style manager
- SQLite database with normalized structure and flexible query system

---

## Design Philosophy

- **Privacy by Design:** No keystroke logging, only filtered activity tracking; no data leaves your machine.
- **Performance by Design:** Runs on low-end hardware, minimal resource usage, efficient data handling.
- **Visibility by Choice:** User can fully configure what’s tracked, labeled, or shown.
- **Documentation for All:** Code is fully documented, even for beginners. Tracking logic is transparent and explainable.

---

## Architecture & Technologies

- **Languages / Frameworks:** Python 3.9+, tkinter, ttkbootstrap, Matplotlib, Pandas, Pystray
- **Database:** SQLite3 (normalized schema with selective JSON usage)
- **Concurrency:** Native `threading` (input tracking, GUI, DB thread)
- **Logging:** Extended `logging` module
- **Config system:** Fully custom-made with distinction between static configs and editable settings
- **Custom UI Toolkit:** Features in-development components from Ouroboros UIX, an upcoming open-source UI framework. The need for a better UIX architecture became clear through ViperTracking itself — this project marks the starting point of its development, and selected elements will be extended and extracted into the framework later on.
> **Platform:** Windows-only (tested on Windows 11, likely compatible with Windows 10)

---

## Use Cases

- Track your daily time spent on applications
- Analyze patterns in productivity and distraction
- Filter specific time ranges, app types, activities, or combinations
- Tag and analyze project work with custom labels (e.g., "Ticket #12345")
- Search what you watched or worked on weeks ago using keywords
- Set parental controls and restrict settings via PIN
- Optional: ignore sensitive categories (e.g., private browsing or specific keywords)

---

## Installation

> **Note:** Pre-Beta versions require manual setup.  
> It is recommended to run the project inside your IDE during development.  
> After the Open Beta, a user-friendly installer will be available for regular use.


- Clone the repository:
  ```bash
  git clone https://github.com/sora7672/vipertracking.git
  ```
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```
- Run the application:
  ```bash
  python main.py
  ```

> A one-click installer (with optional autostart service) and portable version will be provided in the Open Beta.

---

## Privacy & Security

- 100% local execution — no server, no telemetry, no remote logging
- Keystrokes are *not* logged, only categorized (e.g., "gaming keys", "arrow keys")
- In short: your data will always remain your data.
The only exception is if you choose to provide logs for error reporting.
- **See [tracking_logic.py](./src/window_manager.py)** for clear, beginner-friendly documentation of the tracking logic, even understandable for non-technical users.
---

## License & Contribution

- Open Source – **non-commercial use only**
- You may learn from and reference the code, but **commercial reuse is prohibited**
- Contributions may be accepted after Beta release
- A bug report form will be provided via GitHub Pages.
Alternatively, feel free to open an issue directly in this repository.

---

## Why I Built This

Originally, ViperTracking began as a small exercise to learn MongoDB, but it quickly evolved into a deeply personal project. As someone with ADHD, I often struggled to measure time realistically and wanted a tool that helped me see clearly how I use my computer — no assumptions, just data.

Over time, it became my **portfolio foundation**, my **first real architecture**, and something I hope can **motivate others** to pursue their own ideas. I’ve spent over 1300 coding hours on this, overcoming thread deadlocks, architectural rewrites, and even phases of depression and self-doubt.

This project isn’t just about code — it’s about perseverance, learning through doing, and building something that actually helps people understand themselves better.

---

## Devlog

Want to follow the development journey in more detail?  
Read the [Devlog](./docs/devlog.md) for insights, obstacles, architecture decisions, and the thought process behind key features.

This is not just a project, it's a learning path, a reflection and a way to share how I build real tools that grow together with me.

---

## Contact

If you want to get in touch, ask questions, or suggest features:

**Discord:** `sora_7672`  
Feel free to reach out!
Just one thing: if your first message is just "hi" or doesn't include a reason, I probably won't reply.
Be clear from the start. That helps me keep things efficient and spam-free 😊


### For a better mindeset
Always take one step at a time.  
Even if it is a step back, you still learn something from it.  
Every line of code you write can help someone in the future if you give it your best today.

Thanks for reading!  
*Sora_7672*



