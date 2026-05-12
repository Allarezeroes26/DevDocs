"use client";
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function Navbar() {
  const pathname = usePathname();

  const navLinks = [
    { name: 'Chat', href: '/' },
    { name: 'Library', href: '/library' },
    { name: 'About', href: '/about' },
  ];

  return (
    <header className="p-4 border-b bg-white flex justify-between items-center shadow-sm">
      <div className="flex items-center gap-2">
        <span className="text-2xl">🚀</span>
        <h1 className="text-xl font-bold tracking-tight text-blue-600">
          DEVDOCS <span className="text-slate-800">RAG</span>
        </h1>
      </div>
      <nav className="flex gap-6 text-sm font-semibold">
        {navLinks.map((link) => {
          const isActive = pathname === link.href;
          return (
            <Link
              key={link.name}
              href={link.href}
              className={`transition-colors pb-1 ${
                isActive 
                  ? 'text-blue-600 border-b-2 border-blue-600' 
                  : 'text-slate-500 hover:text-blue-600'
              }`}
            >
              {link.name}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}