const ADMIN_WHATSAPP = "966558005545";

export function WhatsAppContact({ lang }: { lang: string }) {
  const ar = lang === "ar";
  const message = ar
    ? "مرحباً، أحتاج إلى مساعدة في تطبيق دوام تك."
    : "Hello, I need help with DawamTech.";
  const href = `https://wa.me/${ADMIN_WHATSAPP}?text=${encodeURIComponent(message)}`;

  return (
    <a
      className="whatsapp-contact"
      href={href}
      target="_blank"
      rel="noreferrer"
      aria-label={ar ? "التواصل مع دعم دوام تك عبر واتساب" : "Contact DawamTech support on WhatsApp"}
    >
      <span className="whatsapp-contact-icon" aria-hidden="true">☎</span>
      <span>{ar ? "تواصل عبر واتساب" : "WhatsApp support"}</span>
    </a>
  );
}
