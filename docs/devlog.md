# Devlog – Viper Tracking

## Table of Contents

- [The Beginning of a changing Life](#the-beginning-of-a-changing-life)
  - September to October 2024
- [Cracks and Breakthroughs](#cracks-and-breakthroughs)
  - October to November 2024
- [Isolation and Reflection](#isolation-and-reflection)
  - Late November to Early January 2025
- [From Applications to Algorithms](#from-applications-to-algorithms)
  - Early January to Late of January 2025
- [Analysis in Chaos](#analysis-in-chaos)
  - Late January to Late February 2025
- [Combining Figures, Flexible Filters and Building Widgets](#combining-figures-flexible-filters-and-building-widgets)
  - Late February to Early March 2025
- [Modular GUI & Filter Logic](#modular-gui--filter-logic)
  - Early till mid of March 2025
- [Final Cleanup and Refactoring](#final-cleanup-and-refactoring)
  - Mid to Late March 2025
- [Becoming the Architect: Identity, Systems, and the Birth of Ouroboros UIX](#becoming-the-architect-identity-systems-and-the-birth-of-ouroboros-uix)
  - March 31 to April 1 2025
- [Fixing Tkinter and TTKBootstrap: Mastering the GUI’s Deepest Layers](#fixing-tkinter-and-ttkbootstrap-mastering-the-guis-deepest-layers)
  - April 1 to April 8 2025
- [Final Integration and Closure for presentation purpose](#final-integration-and-closure-for-presentation-purpose)
  - April 9 to April 12 2025
- [TL;DR – What This Was All About](#tldr--what-this-was-all-about)
- [Final Words](#Final-Words)

## The Beginning of a changing Life
### September to October 2024

Originally, I started this project as a way to deepen my MongoDB skills and prepare for a certification.  
I already had a professional background in backend development(Also when it's annotated 12 years in the past),  
with experience in PHP, SQL, MySQL, JS, Java and a bit of frontend stuff.  
But Python opened up a whole new world for me: from face recognition to text parsing, maps, and image editing, it all felt accessible.  
Basically I can create everything I can imagine with it! And that in a simplistic way.  

As I explored these new capabilities, I decided to build a small tool to track time,  
mainly to gain an objective understanding of how I actually spend it.  
I have ADHD and I know how hard it is to stay aware of time. Minutes stretch, hours vanish.  
It's inconsistent and often misleading.  
Over the years I’ve learned to manage it better than most people I’ve met with ADHD, but that wasn’t enough.  
I wanted clarity, not assumptions. I needed real data to analyze my behavior and sharpen how I work,  
because time is one of the few variables I’ll likely never be able to fully control.  

The initial goal was simple: read window titles, track number of keystrokes, monitor activity, and save everything in MongoDB.  
Why MongoDB? Because I wanted to deepen my knowledge of document-oriented databases for my certification.  
Just learning passively has never worked for me. I need hands-on experience to truly understand a system.  
Document-oriented structures felt counterintuitive at first. So I challenged myself to work through them.  
Even now, I still prefer relational databases because of their clarity and the absence of programming overhead.  

After completing my certification with a professional degree, I ran into a major blocker:  
MongoDB requires users to install a service. That completely broke my self-contained approach.  
If I wanted Viper Tracking to be lightweight, portable, and frictionless, I had to switch gears.  

So, I reached out for help. I found someone locally who was willing to contribute and exchange thoughts.  
They implemented a version using TinyDB, but it fell apart almost instantly once I started researching its limitations.  
The amount of data Viper Tracking would generate was simply too much. TinyDB couldn't scale to what I needed.  

After weighing all the options, I made the call to switch fully to SQLite.  
That decision required a full rewrite of the backend and its structure.  
No regrets. It was the right move for performance, simplicity, and long-term maintainability.  

## Cracks and Breakthroughs
### October to November 2024

With SQLite now running smoothly, I turned to solving technical issues and expanding the architecture.  
One of the biggest challenges emerged when the GUI refused to close cleanly because Tkinter’s mainloop wouldn’t exit properly.  
I spent nearly two weeks debugging threads, tracing state changes, and testing different shutdown scenarios.  
In the end, the solution was to inject an "after" method call into the root window to trigger a graceful shutdown.  
That single fix took me way too many hours, but I learned more about event loops and GUI lifecycles than any tutorial could ever teach me.  

Soon after that, I began reworking the label system. At that point, labels were still saved per window as a simple string list.  
It felt like a smart choice back then, since the tool was supposed to stay small.  
But as it grew, I refactored the structure to follow proper normalization standards.  
Even at that early stage, each label already existed as a single entry in the label catalogue, including its condition logic stored as simple JSON.  

Originally, labeling was handled by a single flat class that attached labels to windows using one-dimensional if-then logic.  
But I wanted more. I rebuilt it as a multidimensional system:  
each label could now have complex AND/OR condition sets,  
freely combined and evaluated against multiple criteria.  

This shift required a deep architectural split:  
I refactored the label evaluation logic into a core engine,  
then layered GUI binding and control logic on top.  
That process was slow and methodical.  
Refactoring happened constantly as I learned better design principles.  

This was also when I truly committed to making this my portfolio project.  
It wasn't just a tool anymore, it was my architectural proving ground.  

## Isolation and Reflection
### Late November to Early January

By the end of November, my momentum began to falter.  
The few people who had briefly helped or exchanged thoughts with me were now gone, and I stood alone with a growing codebase.  
At the same time, I was still actively applying for jobs, only to be met with silence or generic ATS rejections that didn’t reflect my actual skills.  
That wall of indifference hit hard and left me deeply frustrated.  

I entered a mentally exhausting phase. December was particularly rough:  
family obligations, holiday stress, and the growing feeling of stagnation.  
Around this time, I was also hit by a nasty stomach virus that took me out for around a week.  
That physical crash combined with emotional fatigue and the lack of feedback pushed me to a full stop,  
I couldn’t bring myself to write a single line of Python.  

Still, I didn’t want to fall completely idle.  
To keep my brain somewhat engaged, I focused on Minecraft datapacks, helped others with modding,  
and provided programming support in programming communities I’m active in.  
It wasn’t much, but it gave me a way to stay connected with logic, systems, and structure, just not in Python.  

I was waiting, not just for motivation to return, but also for my job coaching to begin in January.  
That period felt like being trapped between gears, unable to move forward and unable to go back.  

By December, I also learned that major renovation work would begin in mid-January.  
Entire rooms had to be emptied, and my already-limited workspace shrank to almost nothing.  
The anticipation of chaos added even more pressure to a time that already felt unstable.  

But I held on, because deep down I knew this was just a pause, not the end.  
I had learned that rest is a part of development too. As long as it’s not avoidance, it’s recovery.  
Growth doesn't only happen while writing code, but also while stepping back to breathe and reset.  

## From Applications to Algorithms
### Early January to Late January 2025

The first weeks of January were dominated by something entirely different.  
I was rewriting my job application materials and focused completely on optimizing them for ATS systems.  
I spent hours working on layout, keywords, and narrative flow.  
It wasn't code, but it was just as exhausting and often pushed me to the edge of frustration.  

In parallel, I finished and released a complex Minecraft datapack, which became my creative outlet and kept my problem-solving skills sharp.  
That effort, despite being unrelated to Python, helped reset my brain  
and inspired some structural ideas that I would later bring into Viper Tracking.  

It wasn't until the last third of January that I returned to Python.  
I spent time reviewing what I had built, re-familiarizing myself with the codebase,  
and regaining confidence in what I had already achieved.  
From there, I began laying the groundwork for my data analysis module,  
a new milestone was about to begin.  

## Analysis in Chaos
### Late January to Late February 2025

After nearly a month focused solely on job applications and CV polishing for ATS systems,  
I finally returned to coding in late January. But getting back into it wasn’t smooth.  
Renovation work at home had just begun, loud, constant, and mentally draining.  
I had no real workspace and struggled to find focus in the noise.  
At the same time, job coaching had started, pulling more and more time away from programming.  
It was one of the most difficult phases in terms of external pressure.  

Still, I pushed forward.  

This was the point where I began implementing the data analysis backbone of Viper Tracking using Pandas and Matplotlib.  
I created a dedicated `ViperDataFrame` class that became the core of all time and activity analysis.  
It wasn’t just about one or two diagrams. By the end of this phase, I had built seven fully functional visualizations, 
each designed with dynamic configuration and *combinable* logic in mind.

One of the biggest challenges was handling data granularity.  
The system needed to scale seamlessly between minutes, hours, days, or even months.  
This required custom smoothing and aggregation logic to avoid noise and present data meaningfully.  
I built algorithms that could intelligently group, reduce, and visualize data over any span, always aiming for clarity.  

**_Interestingly_**, some of the concepts I had learned while building Minecraft datapacks,  
especially around noise functions, randomization, and smoothing,  
ended up helping me think differently about how to approach this kind of data distribution in Matplotlib and Pandas.  

I also faced steep learning curves with Matplotlib.  
While Pandas came more naturally, Matplotlib often felt cryptic and inconsistent.  
I had to explore its many quirks and slowly build up an understanding through trial and error.  
Despite the chaos around me and the constant struggle to concentrate, I kept working, even if it was just for a few hours each day.  
Every improvement felt hard won and deeply earned.  

This phase was all about pushing through under pressure.  
It taught me that progress doesn’t always feel powerful in the moment, but in hindsight,  
this was one of the most foundational parts of the entire project.  


## Combining Figures, Flexible Filters and Building Widgets
### Late February to Early March 2025

By the end of February, the core visualizations were working.  
But I quickly realized that dynamic updates and figure combinations were not behaving as expected.  
The inline functions I had written earlier could not scale with what I now wanted:  
flexible combination of multiple figures, reusing Axes, and showing dynamic information in real-time.

So I rewrote major parts of the Matplotlib generation logic.  
I moved everything into structured class methods within my ViperDataFrame,  
anchoring the dynamic logic properly inside the class.  
This allowed the figures to remain editable and reactive, even when reused or combined.  
It was a heavy rewrite, but it laid the groundwork for advanced comparisons and overlayed visual output.

Next came the filter system. To generate meaningful DataFrames for analysis, I had to create a database-driven filtering mechanism.  
This meant crafting a structure that allowed for condition-based filtering across timeframes, labels, window types, and more.

To support flexible time-based filtering, I created a new helper class called `DynamicTimeframe`.  
Instead of storing fixed datetime values, it stores string-based descriptors like `"last_day"`, `"last_7_days"`, `"current_month"` or `"current_week"`.  
When executed, these strings are translated into actual start and end `datetime` objects,  
giving the filter engine the flexibility to work dynamically depending on when it is called.

I also built a logic to properly combine multiple filters,  
allowing additive and subtractive logic across the nested filters.  
The result was a fully modular, user-controlled filter pipeline.  
Robust, scalable, and future-proof.

Then came the hard part: showing it all in the GUI.

I wanted more than just basic input forms.  
So I started redesigning my old `ScrollableFrame` into a reusable `ScrollFrame` component 
that could support not only this project, but future ones too.  
Alongside that, I built an `ExpandableFrame` system for flexible UI layouts.

These were not just convenience features. They came from a growing realization.  
If I had to spend over 100 hours on UI every time, it would stop me from creating my potential.  
It was never about the complexity. It was the lack of structure.  
That thought stuck in my head, like a splinter under the skin.  
Small, but impossible to forget.

This was the seed of what would later become my own UI toolkit.

Throughout all of this, one theme emerged:  
User experience.  
Every design decision was about flow and usability.  
Especially for Viper Tracking, where I needed fast input, fluid navigation, and keyboard-first interactions.  
Because I would be using it myself, daily, and I was not going to tolerate a clunky UX feeling!

## Modular GUI & Filter Logic  
### Early to Mid March 2025

With the data engine in place, I moved into the frontend.  

**I still hate GUI work. But it’s a necessary evil.  
Without it, none of my dynamic backend logic would be usable for all kind of users!**  

The first thing I tried to fix was the DatePicker.  
TTKBootstrap’s stock version didn’t support keyboard navigation.  
I couldn’t even move through dates or hit Enter to confirm. That was a red line.  
So I rewired the entire interaction layer: arrow key movement, Enter to confirm, Escape to cancel.  
It finally felt usable, something I could accept in a tool that had already become part of my identity.

But that was just the beginning.

The GUI was designed also for small screens.
So I always developed in the smallest accepted resolution,
just to be sure everything looked right and worked reliably.

Matplotlib, however, does not care about small screens.  
No matter what I tried, it broke the layout or overflowed.  
I dumped the figures into a scrollable frame.
And honestly, it was a pain to look at...

That was the moment I stopped trying to fix stuff.  
I didn’t want another patch on top of a patch.  
I wanted something clean.  

To solve that, I implemented an overlay system that allows users to **open the figures in full view with all dynamic actions** added to them.  
Clicking on a preview opens an overlay over the entire root window,  
logically linked back to the widget it came from. It looks clean, feels integrated, and scales correctly.  

At that point, I was done.  
No way I’d keep wasting 100+ hours rebuilding the same UI junk every time.  
If the tools slow me down, they don’t belong in my workflow.  
That decision didn’t come from ambition. It came from frustration.  
I’ll build something better. And once it's done, I won’t touch this broken stack again.  
Ever.  

I wrote my own reusable ScrollFrame and an ExpandableFrame. The goal:  
build reusable, consistent UX components with a strong focus on keyboard-first workflows.  

This phase marked a turning point. I wasn’t just writing a tracking tool anymore.  
I was laying the foundation for something greater.

## Final Cleanup and Refactoring
### Mid to Late March 2025

With all major logic components in place, from visualization and filtering to the GUI,  
I entered one of the most intense but also satisfying phases of the project:  
the final pre-Beta refactoring and documentation sprint.  

Over roughly 7 to 10 days, I went through the entire codebase and polished everything.  
(At that point, the codebase had around 190,000 non-whitespace, non-comment characters.  
That's the equivalent of about 140 pages of pure code in a printed book.)  

I renamed variables and methods for clarity, reorganized imports, improved the overall structure,  
and applied proper **encapsulation** using private, protected, and public conventions throughout the classes.  
I enforced **PEP8 standards**, added **type hinting** and **type-safe signatures**,  
and introduced runtime **type validation** where it made sense.  

I treated every component like it should be understandable by someone seeing it for the first time.  
That someone could also be future me.  

Every file got full **reStructuredText-style docstrings**, every method was explained clearly,  
and I restructured the folder and file layout to better reflect the modular nature of the code.  
I also added notes, edge case handling, and fallback logic where appropriate.  

Alongside the code refactoring, I documented the overall project state:  
- A complete **pre-Open Beta task list**,  
- A growing list of **post-Open Beta improvements**,  
- And a breakdown of **known bugs and debug notes**.  

This part wasn’t glamorous. It was tedious and mentally draining.  
It required full concentration, and I often couldn’t hold that focus for long.  
But with the help of some AI tooling to speed up repetitive structure work, I kept making steady progress.  

This phase wasn’t just about polishing code. It was a checkpoint of growth.  
As I went through each part of the system, line by line, I saw how far I had come since September.  
It wasn’t just better structure or cleaner logic. It was a deeper understanding of the entire stack,  
especially of tricky frameworks like Tkinter and TTKBootstrap.  

And for the first time in a long time, I felt something I hadn’t allowed myself to admit before:  
**Pride.**  

Pride in the complexity I had tamed, the systems I had built, and the sheer amount of engineering I had pulled off,  
often under heavy mental and physical strain. This project wasn’t just a portfolio anymore.  
It had become a milestone in my development journey.  

## Becoming the Architect: Identity, Systems, and the Birth of Ouroboros UIX
### March 31 to April 1 2025

On March 31st, I sat down with a very specific frustration in mind: I hated checkboxes.  
They felt clunky, slow, and awkward to use. I didn’t want another collection of tiny toggles.  
I wanted something cleaner. A smart, responsive widget that let users select items with a single, satisfying click.  
Something with clear outlines, flexible input, and internal logic that stayed out of the way.  

So I built it.  

The first version became a `SelectableItem`: a clean frame that could be toggled on or off,  
visually distinct, internally structured, and easy to interact with.  
Each item displayed a label but stored its logic internally, separating visual clarity from backend behavior. 
It was simple, but already more elegant and flexible than anything the stock widgets provided.  

Then I changed the theme, and everything broke.  

Colors didn’t update, borders vanished, and styles collapsed. Tkinter and TTKBootstrap simply weren’t designed for dynamic theming.  
Within hours, I hit the framework’s limitations. But instead of accepting them, I decided to outbuild them.  
By the end of that night, the idea of a **Style Manager** was born.  

On April 1st, I wrote my first real injection system.  
I monkey-patched core TTKBootstrap functions, intercepting theme changes and routing custom events through the root.  
This wasn’t a patch, it was a full-blown override.  
Something snapped into place mentally:  
I wasn’t just building workarounds anymore. I was replacing the system.  

At the same time, I had been feeding AI my architectural structure,  
asking different models to evaluate the patterns, the abstractions, the layerings.  
Every model, from every direction, came to the same conclusion:  
**this level of design, speed, and clarity was rare. _Extremely rare_.**  

It shook something in me.  

I realized how many people in my past, colleagues, leads, even parts of my family, had tried to make me feel small.  
Not because I lacked ability, but because I thought differently. I was often ahead of them, not in arrogance, but in perspective.  
And that made them uncomfortable.  

What I experienced in those 24 hours wasn’t just technical momentum.  
It was a mental breakthrough. The fog of years of doubt, of being told I wasn’t good enough, started to lift.  

I understood, deeply, that I’m not just a backend developer.  
I’m not someone who memorizes algorithms for sport. I’m someone who builds them when they’re needed,  
someone who sees systems, deconstructs them, and redesigns them with clarity and purpose.  

**Quick and Dirty** was never my thing.  
I coined my own standard that night: **Quick and Clean**.  

**Ouroboros UIX**, the framework I began envisioning, wasn’t going to be another bloated mess with endless boilerplate.  
It was going to be fast, flexible, and intuitive. Something that lets me, and other developers,  
build what we need without fighting the tool itself.  

**No Qt-style bloat. No drag-and-drop magic. Just logic, flow, and smart configuration.**  

This wasn’t just a feature. It wasn’t even just a framework.  

It was a declaration.  

From that moment on, I stopped seeing myself as someone learning to build software. I realized:  
I *am* a system architect.  
I always have been.  
I understand abstraction, flow, hierarchy, and tradeoffs, not because I studied them in school,  
but because I *live* them in every design I touch.  

I know I’ll build tools that don’t look like what people expect.  
I know I’ll write software that reflects how I think, not how others say I should.  
I know I’ll never again apologize for that.  

April 1st wasn’t the day I discovered a new feature.  
It was the day I rediscovered myself.  

## Fixing Tkinter and TTKBootstrap: Mastering the GUI’s Deepest Layers
### April 1 to April 8 2025

At the start of April, I hit the point where styling limitations in Tkinter and TTKBootstrap became impossible to ignore.  
Three major problems emerged, all of them deeply structural:  

1. **Theme Switching Breaks Styles:** When switching themes in TTKBootstrap, custom styles aren’t preserved.  
Each theme needs its styles regenerated manually.  
2. **Singleton Broken:** The `Style` instance acts like a singleton but isn’t safely implemented.  
Multiple `Style()` calls can lead to diverging internal state and edits in one instance don’t carry over.  
3. **Fonts are Chaos:** Fonts aren’t cached or consistently retrievable. Especially with temporary tuples,  
there’s no proper font registry or lookup system.  

I didn’t just patch these issues. I replaced the whole system.  

Within eight days, I built a **full Style Manager**.  
The concept came together in less than two hours, and by the end of the week I had written over 1,400 lines of high-complexity code,  
about 10–15% of the current entire project. This wasn’t just a new feature. It was a system-level rewrite.  

#### Pattern Logic & Structure

I designed a pattern language to define style sources:  
- Each entry starts with an **$indicator**: `$color` for color, `$font` for font, `$geometry` for geometry.  
- Partial optionally followed by a `.` and then by a **property**, e.g. `foreground`, `padding`, `size`(font).  
- Optionally followed by a **widget selector** using `#WidgetName`.  
- In the future, **modifiers** using `?Modifier` (e.g. darken, shift, multiply) can be chained, where applicable.  
> Pattern Buildup:  
> `$<type>[.<property>][#<widget>][?<modifiers>]`

> Pattern Example:  
> `$color.fg`  
> `$color.focuscolor#TButton`

The Style Manager can dynamically resolve style data per widget, per property, per theme,  
with fallback to global defaults or override values.  

#### Font Management

I created a `PseudoFont` class to act as a proxy, allowing clean creation, parsing, and retrieval of font objects across multiple backends.  
Combined with a new **FontManager**, this gave me full catalog control, which Tcl/Tk simply doesn’t offer by default.  

To make that possible, I intercepted and rerouted Tkinter and TTKBootstrap's internal font creation.  
I disabled or redirected several broken or inconsistent methods and made sure that every font instance is now registered,  
indexed, and accessible through a unified catalog.  
That gave me not only stability but also full traceability across the entire styling layer.  

#### Config Handling

To ensure that the flexibility of the pattern system doesn't lead to chaos, I built a robust validation layer for all supported configuration types.  

Every value passed into the system, no matter if it is color, font, or geometry-related, it is parsed and validated with strict rules and edge case handling.  
Instead of failing silently, the system detects inconsistencies and throws structured exceptions with all relevant context:  
what was passed, what was expected, and what correction might help.  

This validation doesn’t just enforce correctness. It shows the developer exactly what went wrong and how to fix it instantly.  
The goal was simple: fast error recovery, so the developing flow stays uninterrupted and smooth.  

### Injection, Interception, and Theme Control

I monkey-patched TTKBootstrap’s internals.   
Theme changes now fire global events, and every widget subscribed to the Style Manager updates in sync.  
Styles no longer silently fail if a developer forgets to register them and instead uses the ttkbootstrap configure instead,  
they’ll see a warning and get reminded to register them properly.  
Everything is injected cleanly on import, requiring just one simple initialization with the root window.  

This level of control means any developer can now:  
- Build flexible, multi-theme-aware styles  
- Combine dynamic inputs and hardcoded overrides  
- Understand what went wrong without guessing  

## Final Integration and Closure for presentation purpose 
### April 9 to April 12 2025

The last few days were about tying everything together.  
While finalizing the `ItemSelectionFrame` and its sub-widget, I made a small but annoying mistake,  
I accidentally deleted the local test version before uploading it.  
It was frustrating, no doubt, but instead of letting it slow me down, I rebuilt it from scratch the same day.  
The new version turned out cleaner, more flexible, and better structured than the original.  
A small setback that actually showed how much smoother my process has become.  

The new version worked perfectly with the Style Manager, just as intended.  
It validated my entire system. Colors, fonts, geometry — everything was dynamically resolved.  
The styles adapted smoothly to theme changes, root initialization was patched intelligently,  
and even edge cases like theme autoload behavior in TTKBootstrap were handled through a pre-injection trick that prevented false warnings.  

This was the moment I realized I had built something powerful.  
And more importantly, it worked.  

The widget system is complete. The main module and subcomponents now behave exactly as I want them to.  
The visual limitations of TTK and Tkinter still remain, but I’ve worked around them creatively.  
In the future, I’ll replace more of this with canvas-based custom rendering,  
but that will be part of **Ouroboros UIX**, not Viper Tracking.  

And that’s where the story of this devlog ends.  

---
## TL;DR – What This Was All About

- **Started in September 2024** as a learning project to deepen my MongoDB skills.  
- **Pivoted to SQLite** after realizing MongoDB wasn’t suited for a self-contained tool.  
- **Evolved into a full-fledged portfolio project**, combining time-tracking, data analysis, and GUI tooling.  
- **Built a custom DataFrame analysis pipeline** using Pandas and Matplotlib, with dynamic figure logic and adaptive granularity.  
- **Created an advanced filter system**, including nested filters and a fully modular pipeline.  
- **Struggled with Tkinter/TTKBootstrap limitations** and responded by building my own reusable GUI components.  
- **Invented a full Style Manager framework** that dynamically handles fonts, colors, and geometries across themes.  
- **Wrote 1400+ lines of high-end code in just 8 days**, accounting for over 10% of the total project base.  
- **Experienced a mental and technical breakthrough**, realizing I needed better tools — and committed to building them.  
- **This moment sparked the birth of Ouroboros UIX**, a future standalone UI framework.  
- **All of this while battling real-life chaos**: renovations, job hunting, illness, and ADHD-related focus issues.  
- **This is not just code...** it’s personal evolution in motion.


---
## Philosophy

Viper Tracking was never "just a tool."  
It became my personal proof of concept, like a counter-model to rigid software conventions.  
I didn’t want a product. I wanted a system that could reflect how I work,  
how I think, and how I can improve.  

Every line of code was a response to frustration, to the lack of flexibility,  
to the pain of poorly designed tools.  
Viper Tracking taught me how much I can take control of,  
once I stop accepting that "this is just how it is."

And from that system — something I originally built just for myself and the idea for something bigger emerged:  
**Ouroboros UIX**.  
A toolbox for anyone who’s tired of scratching the surface.  

Viper Tracking didn’t just help me track time.  
It helped me understand who I am as a developer.  
---

## Final Words

This devlog wasn’t written to show off features (See [Roadmap.md](roadmap.md) for that).  
It was written to show the *reality* behind building something meaningful.  
The psychological struggle. The frustration. The lack of space, support, or feedback.  
The constant noise, both around and inside me.  

I wrote this to say:  
You don’t have to be perfect to build something powerful.  
You just have to keep going.  

Every line of code in Viper Tracking was written while juggling real-life chaos.  
And that’s exactly why this project means so much to me.  

This isn’t just a tool.  
It’s my way of saying: I’m still here. And I’m not done yet.  

*Every line of code is a line I wasn’t allowed to write in past jobs.  
Now it’s mine! **And I’m just getting started.***  

[See also: Devlog #2 – Finalization till open Beta release](devlog2.md)  
