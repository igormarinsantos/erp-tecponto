import whatsappOutline from "../assets/whatsapp-outline.svg";

interface WhatsAppLogoProps {
  className?: string;
  size?: number;
  title?: string;
}

export function WhatsAppLogo({ className, size = 20, title = "WhatsApp" }: WhatsAppLogoProps) {
  return (
    <img
      aria-label={title}
      alt=""
      className={className}
      height={size}
      role="img"
      width={size}
      src={whatsappOutline}
    />
  );
}
