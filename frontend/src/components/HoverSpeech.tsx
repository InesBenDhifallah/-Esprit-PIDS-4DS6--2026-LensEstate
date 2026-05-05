import { useEffect, useRef } from "react";
import { useAccessibility } from "@/context/AccessibilityContext";

export function HoverSpeech() {
  const { isHoverSpeechEnabled: isEnabled } = useAccessibility();
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!isEnabled) return;

    const handleTrigger = (e: MouseEvent | FocusEvent) => {
      const target = e.target as HTMLElement;
      const isSpeakable = target.closest('p, h1, h2, h3, h4, h5, h6, button, a, label, li, [data-speak]');
      
      if (!isSpeakable) return;

      const element = isSpeakable as HTMLElement;
      const textToSpeak = element.getAttribute('data-speak') || element.innerText;

      if (!textToSpeak || textToSpeak.trim() === "") return;

      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      window.speechSynthesis.cancel();

      timeoutRef.current = setTimeout(() => {
        const utterance = new SpeechSynthesisUtterance(textToSpeak);
        utterance.lang = 'en-US';
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        window.speechSynthesis.speak(utterance);
      }, 300);
    };

    const handleCancel = () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      window.speechSynthesis.cancel();
    };

    window.addEventListener('mouseover', handleTrigger);
    window.addEventListener('focusin', handleTrigger);
    window.addEventListener('mouseout', handleCancel);
    window.addEventListener('focusout', handleCancel);

    return () => {
      window.removeEventListener('mouseover', handleTrigger);
      window.removeEventListener('focusin', handleTrigger);
      window.removeEventListener('mouseout', handleCancel);
      window.removeEventListener('focusout', handleCancel);
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      window.speechSynthesis.cancel();
    };
  }, [isEnabled]);

  return null;
}
