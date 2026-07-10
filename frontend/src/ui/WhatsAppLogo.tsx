interface WhatsAppLogoProps {
  className?: string;
  size?: number;
  title?: string;
}

export function WhatsAppLogo({ className, size = 20, title = "WhatsApp" }: WhatsAppLogoProps) {
  return (
    <svg
      aria-label={title}
      className={className}
      height={size}
      role="img"
      viewBox="0 0 32 32"
      width={size}
      xmlns="http://www.w3.org/2000/svg"
    >
      <circle cx="16" cy="16" fill="#25D366" r="15" />
      <path
        d="M23.1 8.8A9.9 9.9 0 0 0 7.5 20.7L6.3 25l4.4-1.1A9.9 9.9 0 0 0 25.9 15.5a9.8 9.8 0 0 0-2.8-6.7Zm-7.1 15a8.2 8.2 0 0 1-4.2-1.1l-.3-.2-2.6.7.7-2.5-.2-.4a8.2 8.2 0 1 1 6.6 3.5Zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1-.2.3-.7.9-.9 1.1-.2.2-.3.2-.6.1-1.7-.8-2.8-1.5-3.9-3.3-.3-.5.3-.5.8-1.5.1-.2 0-.4 0-.5l-.8-1.9c-.2-.5-.4-.4-.6-.4h-.5c-.2 0-.5.1-.7.4-.3.3-1 1-1 2.3s1 2.7 1.1 2.9c.1.2 1.9 3.1 4.8 4.2 1.8.8 2.5.8 3.4.7.5-.1 1.5-.6 1.7-1.3.2-.6.2-1.2.2-1.3-.1-.2-.2-.3-.5-.4Z"
        fill="#fff"
      />
    </svg>
  );
}
