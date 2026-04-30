# Vibelton v2 Architecture: Two-Mode System

To avoid overwhelming new users during onboarding, we will separate the Vibelton experience into two distinct, purpose-driven modes. This conceptual split allows us to integrate the "Making Music" strategies cleanly, guiding the user based on where they are in their creative process.

## User Review Required

> [!IMPORTANT]
> Please review the proposed split of the app into two modes. Does the color scheme and naming convention (Idea Engine vs. Finisher) align with the brand?

## The Two Modes

The web UI will be split into two main tabs or standalone pages, each with its own distinct visual identity to clearly indicate which "brain" of Vibelton the user is interacting with.

### 1. Vibelton: Idea Engine (Overcoming "Blank Page Syndrome")
**Target Audience:** Users starting from scratch or struggling to find inspiration.
**Visual Identity:** Bright, energetic, and generative (e.g., Neon Green, Electric Blue, vibrant gradients). The UI feels open and full of possibilities.

**Core Features (From the Guide):**
*   **Genre DNA Generator:** The core Vibelton feature. The user types a prompt, and the engine generates a full starting loop.
*   **Mise en Place (Studio Setup):** The AI populates an Ableton template with 8 high-quality tracks (Drums, Bass, Chords, Leads) but *no MIDI data*. It simply prepares the perfect canvas for the user to play on.
*   **Arbitrary Constraints:** The AI generates a random constraint for the session to spark creativity (e.g., "Use only 3 tracks", "No hi-hats").
*   **Avoidance Prompts:** The AI suggests things *not* to do, forcing the user out of their comfort zone.

### 2. Vibelton: The Finisher (The "Money Shot" Maker)

> [!WARNING]
> **Non-Destructive Workflow Requirement:** The Finisher must *never* delete or overwrite original user data. When applying mutators or structural changes, the engine must duplicate the target track(s), mute the originals, and apply the changes to the new track. Additionally, the UI should still explicitly prompt the user to "Save a Copy" of their Ableton Live Set before making sweeping changes for maximum safety.

**Target Audience:** Users who have a basic 8-bar loop but are stuck, fatigued, or don't know how to turn it into a full song.
**Visual Identity:** Deep, focused, and analytical (e.g., Deep Purple, Amber, Crimson, sleek dark mode). The UI feels like a precision tool for sculpting and arranging.

**Core Features (From the Guide):**
*   **The Mutator:** Select an existing MIDI clip and have the AI generate "siblings" (Mutation of Clones). It applies one meaningful change per iteration (e.g., adding ghost notes, inverting the melody, humanizing the groove).
*   **Maximal Density Mode:** The AI generates a "Drop" scene where every instrument is playing at once. The user then copies the scene and mutes clips to carve out the intro and verses (Arranging as a Subtractive Process).
*   **Formal Skeletons:** The AI injects standard genre song structures (Intro, Verse, Chorus, Breakdown, Drop) into the Ableton arrangement view using locator markers.
*   **Automation Rhythm Generator:** The AI creates rhythmic automation envelopes (like filter sweeps) on existing static synth chords to add life and movement.

---

## Implementation Strategy

### 1. UI / UX Overhaul
*   Update the front-end (web folder) to support a global toggle between **Idea Engine** and **The Finisher**.
*   Implement dynamic CSS theming so the entire app changes color and vibe when switching modes.
*   Keep the onboarding flow restricted to the **Idea Engine** by default, introducing **The Finisher** only after the user has successfully generated or loaded an initial idea.

### 2. Backend Routing
*   Create separate Python modules or classes for handling the logic of each mode (e.g., `idea_engine.py` vs `finisher_tools.py`) to keep the codebase clean.
*   Ensure `actions.py` exposes distinct endpoints for generative prompts vs. mutative/arrangement tools.

### Next Steps

1.  **Approve the Modes:** Confirm the feature split and the visual direction.
2.  **Design Update:** Begin working on the CSS and HTML structure to support the two modes.
3.  **Backend Integration:** Start wiring up the first set of "Finisher" tools (like the MIDI mutators) to the new UI.
