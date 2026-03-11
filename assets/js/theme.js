/**
 * Theme toggle — switch between light and dark modes.
 *
 * Persists the user's preference to localStorage so it survives
 * page navigations and reloads.  The initial theme is applied via
 * an inline script in &lt;head&gt; to prevent a flash of wrong theme.
 *
 * @module theme
 */

/**
 * Toggle between light and dark themes.
 * Updates the data-theme attribute on the root element and saves
 * the choice to localStorage.
 */
function toggleTheme() {
    const html = document.documentElement;
    const next = html.getAttribute("data-theme") === "dark" ? "light" : "dark";
    html.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
}
