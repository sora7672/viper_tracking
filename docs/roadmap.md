# Roadmap - What we reached and where we reach out to

## Table of Contents

- [Disclaimer](#disclaimer)
- [Pre Open Beta](#pre-open-beta)
- [Post Open Beta](#post-open-beta)
- [Potential Feature Ideas](#potential-feature-ideas)
- [Milestones Completed](#milestones-completed)

## Disclaimer

This roadmap is a guide for me, to track what’s done, what’s in progress, and what’s still ahead.  
It is also a promise to you, to show what I’ve envisioned and where the journey leads.  

It’s not a timeline. It’s a direction. Some features may be finished in a day.  
Others may wait, while I work on different tools or handle things outside of code.  
I work in bursts of high focus, driven by clarity and curiosity, not by pressure.  
This roadmap exists to capture technical depth and vision, not deadlines.  


If you're looking for a more personal and detailed insight into the process,  
how things were built, what challenges came up, and what it all meant, you want to read this:<p style="font-size: 14px;">[**Devlog**](devlog.md)</p>


## Pre Open Beta
This is a list of features that I absolutely want to finish before releasing the first open beta.
(But because of IRL and time reasons they are not done yet)  

- Add Mainplot label logic & UI & UX
- Fix subfilter remove and then error on analyse
- Prevent double opening of main window
- Make the app closing with a confirmation
- Fix window process error, which occurs when there is time between process id grab & process analysis(lag or so)
- Handle no values on plot and analysis(if not fixed so far)
- Save colors for labels, also in db
- Save colors for apps, also in db
- Enable logging in debug mode & hardcore debug mode in GUI
- Add logics for logging hardcore debug and normal debug
- Fix reading in GUI themes from config
- Add logger to the newer modules
- Create a smarter DB exception handling
- Minimize all imports in each module to `from xyz import methode, methode2` and so on
- Check for scattered prints or bad raises per module
- Hook in the day analyzer in main_view, not the static data for tests


## Post Open Beta
Here you will see my planed features or mechanics I will start implementing after the program is available to install  
on the pc. Most of them are not needed for the core functionality, but in my opinion either helping the use of the tool  
or visual optimizations or just refactors, to make the code better (but basically won't change how it works).  

- Bug/Issue report area near settings view, linked to GitHub & filtering duplication entrys
- Window labeling conditions with dynamic timeframes, like weekday(monday, tuesday etc.), or daytime(morning, evening, etc.)
- ConfigManager & SettingsManager total refactor to implement my better coding style
- All modules outsource common methods/functions into utility modules for better encapsulation
- Create *`Ourbobors UIX`* Framework and implement it here, to crack open the monolith GUI Views
- Create better widgets, also as part for *`Ourbobors UIX`*
- Better Validation logic with *`Ourbobors UIX`*
- Add also weekdays, daytime dynamic search for filters
- Complete rework of ViperDF, including optimizations and initialization handling
- Also probably split the ViperDF to a pandas(analysis only) and matplot(figure generation only) module
- Outsource DayAnalyzer in own module
- Rework the old ViewController
- Outsource custom exceptiosn & rework them to have the same standard here
- Add some small helper function like "smart_copy" and recheck all return values for protection
- Add privacy protection area, where keywords or applications can be blacklisted to not be tracked


## Potential Feature Ideas
What you see here, is a thought collection of stuff, that I would flag as "nice to have" but not "needed to have",  
including some future optimizations, mechanics and more.

- Instead of saving database querrys with dicts/direct values, maybe add some smarter Databaseobject to
forward between modules?
- Database setup rechecking. Maybe some architecture, like locks are not needed in this project context.
- Tk Scaling, maybe a nice feature for people who have bad eyes, but need further testeing
- Add a parenting control, because people will so or so use it like that, why not give them proper toolings?
Should include a pin to close app, same pin for changing settings (But still we will add here enforced privacy!)
- Export of analysis, in form of csv or sql, not as 5 seconds frame, but as combined output from pandas.
- Backup creation & backup import, maybe even adding here the option to upload anyhwere?


## Milestones Completed

A list of major features, systems, and breakthroughs already implemented.  
This isn’t just "done", these are key stepping stones that shaped the core of Viper Tracking.  

- a
- b
- c

