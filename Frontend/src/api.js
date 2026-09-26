// The one place the backend's base URL is defined. Everything else
// imports API_BASE from here instead of hardcoding localhost — that
// hardcoding is exactly what breaks the site for anyone not on this
// laptop. Set VITE_API_BASE in Frontend/.env to the backend's public
// tunnel URL so it works from any device.
export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
