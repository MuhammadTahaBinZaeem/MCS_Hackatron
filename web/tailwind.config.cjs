module.exports = {
  content: ['./index.html', './src/**/*.{ts,tsx}'], darkMode: 'class',
  theme: { extend: { colors: {
    background: 'var(--background)', foreground: 'var(--foreground)', card: 'var(--card)',
    'card-foreground': 'var(--card-foreground)', primary: 'var(--primary)',
    'primary-foreground': 'var(--primary-foreground)', secondary: 'var(--secondary)',
    'secondary-foreground': 'var(--secondary-foreground)', muted: 'var(--muted)',
    'muted-foreground': 'var(--muted-foreground)', accent: 'var(--accent)',
    'accent-foreground': 'var(--accent-foreground)', border: 'var(--border)', input: 'var(--input)',
    ring: 'var(--ring)', destructive: 'var(--destructive)', sidebar: 'var(--sidebar)', 'sidebar-accent': 'var(--sidebar-accent)'
  }, borderRadius: { md: 'calc(var(--radius) - 2px)', lg: 'var(--radius)', xl: 'calc(var(--radius) + 4px)' } } }
}
