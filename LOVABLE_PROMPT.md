# NeoFeed — Lovable Frontend Prompt

Copy-paste this into Lovable to generate the frontend.

---

## PROMPT:

Build a single-page news aggregator dashboard called **NeoFeed** with a dark, futuristic Matrix-inspired theme. This connects to a REST API backend.

### Theme & Design

- **Background**: Deep black (#0D0D0D) with a subtle animated Matrix-style falling green characters rain effect (very faint, in the background, should not distract from content)
- **Primary color**: Matrix green (#00FF41)
- **Secondary**: Dark green (#003B00), muted green (#008830)
- **Accents**: Subtle cyan (#00FFFF) for hover states
- **Borders**: Glowing green borders with a subtle box-shadow glow effect
- **Typography**: Use `JetBrains Mono` or `Fira Code` for headings and labels. Use `Inter` or system sans-serif for body text.
- **Cards**: Dark card backgrounds (#111111) with green border, slight green glow on hover
- **Scanline overlay**: Very subtle horizontal scanline CSS effect across the entire page (opacity 0.03)
- **Overall feel**: Like you're reading a hacker's classified intelligence terminal

### Pages / Views

#### 1. PIN Login Screen
- Full-screen centered card
- Large "NEOFEED" title in monospace with letter-spacing: 8px, glowing green
- Subtitle: "Access Terminal"
- PIN input field (numeric, masked like ••••)
- "ENTER" button
- API: `POST /auth/verify` with body `{ "pin": "1234" }`. Store authenticated state in localStorage.
- All subsequent API calls include header `X-Pin: <pin>`

#### 2. Main Feed (after login)
- **Top navigation bar**:
  - Left: "NEOFEED" logo text (glowing green, monospace)
  - Center: Three tab buttons: `ALL` | `AI` | `CRYPTO` (filter by category)
  - Right: Search input field with green border, and a gear icon for settings
- **Main content area**: Scrollable card-based feed
- **Each card represents a news cluster** and shows:
  - **Trust badge** (top-left corner):
    - ✅ green badge = "VERIFIED"
    - 🟢 light green badge = "LIKELY TRUE"
    - 🟡 yellow badge = "UNVERIFIED"
    - 🔴 red badge = "LIKELY FALSE"
  - **Title** (representative_title from cluster) — bold, green, clickable
  - **Summary** — 2-3 lines, muted green text
  - **Metadata row**: source count ("from 4 sources"), category pill (AI/CRYPTO), importance stars (⭐ based on importance_score / 2, max 5)
  - **Upvote / Downvote buttons** (left side, vertical, like Reddit) — green arrows, filled when active
  - **"Sources" expandable section** — click to show all articles in the cluster with their individual source names and links
  - Cards should have a subtle slide-in animation on load
- **API calls**:
  - `GET /clusters/?category=ai&personalized=true&limit=50` for cluster list
  - `GET /articles/cluster/{cluster_id}` when expanding sources
  - `POST /votes/` with `{ "cluster_id": "...", "vote": "up" }` or `"down"`

#### 3. Sidebar (right side, collapsible)
- **Trending Topics**: Show top keywords from recent articles
- **Your Stats**: Simple display of preference weights (how much you lean AI vs Crypto, favorite sources)
  - API: `GET /preferences/`
- **Filters**:
  - Trust rating filter (checkboxes: Verified, Likely True, Unverified, Likely False)
  - Minimum importance slider (1-10)

#### 4. Settings Panel (modal or separate view)
- Change PIN section
- Manual trigger buttons: "Scrape Now" (`POST /admin/scrape`) and "Send Digest" (`POST /admin/digest`)
- Display API connection status

### API Configuration

The backend URL should be configurable via an environment variable or a settings field. Default to `http://localhost:8000`. All requests need the `X-Pin` header after login.

### Technical Requirements

- Use React with TypeScript
- Use Tailwind CSS for styling
- Use Supabase JS client only if needed for real-time features (optional)
- Responsive design: works on desktop and mobile
- Smooth animations (framer-motion or CSS transitions)
- Use `@fontsource/jetbrains-mono` for monospace font

### Component Breakdown

1. `MatrixRain` — background canvas animation (subtle falling characters)
2. `PinLogin` — login screen
3. `NavBar` — top navigation with tabs and search
4. `FeedCard` — individual news cluster card with trust badge, votes, expandable sources
5. `Sidebar` — trending, stats, filters
6. `TrustBadge` — colored badge component
7. `VoteButtons` — upvote/downvote with API integration
8. `SettingsModal` — settings panel

### Color Reference

```
--bg-primary: #0D0D0D
--bg-card: #111111
--bg-card-hover: #1A1A1A
--green-primary: #00FF41
--green-dark: #003B00
--green-muted: #008830
--green-dim: #00AA30
--cyan-accent: #00FFFF
--red-alert: #FF0040
--yellow-warn: #FFD700
--text-primary: #00FF41
--text-secondary: #008830
--text-muted: #003B00
--border: #003B00
--border-glow: 0 0 10px rgba(0, 255, 65, 0.3)
```
