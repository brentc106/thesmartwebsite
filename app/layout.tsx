import type { Metadata } from 'next';

export const metadata: Metadata = {
  metadataBase: new URL('https://www.thesmartwebsite.co'),
  title: 'The Smart Website Co. — Websites & AI for Australian Tradies',
  description: 'Free business audit. Website rebuild from $497 with 14-day delivery guarantee. AI chatbot and receptionist for Australian tradies and small businesses.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Montserrat:wght@500;700;900&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body style={{ margin: 0, padding: 0, background: '#080808' }}>{children}</body>
    </html>
  );
}