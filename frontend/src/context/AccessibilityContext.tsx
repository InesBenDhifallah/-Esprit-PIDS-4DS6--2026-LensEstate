import React, { createContext, useContext, useState, ReactNode } from "react";

interface AccessibilityContextType {
  isHoverSpeechEnabled: boolean;
  toggleHoverSpeech: () => void;
  isVoiceNavEnabled: boolean;
  toggleVoiceNav: () => void;
}

const AccessibilityContext = createContext<AccessibilityContextType | undefined>(undefined);

export function AccessibilityProvider({ children }: { children: ReactNode }) {
  const [isHoverSpeechEnabled, setIsHoverSpeechEnabled] = useState(false);
  const [isVoiceNavEnabled, setIsVoiceNavEnabled] = useState(false);

  const toggleHoverSpeech = () => setIsHoverSpeechEnabled(!isHoverSpeechEnabled);
  const toggleVoiceNav = () => setIsVoiceNavEnabled(!isVoiceNavEnabled);

  return (
    <AccessibilityContext.Provider value={{ 
      isHoverSpeechEnabled, toggleHoverSpeech, 
      isVoiceNavEnabled, toggleVoiceNav 
    }}>
      {children}
    </AccessibilityContext.Provider>
  );
}

export function useAccessibility() {
  const context = useContext(AccessibilityContext);
  if (context === undefined) {
    throw new Error("useAccessibility must be used within an AccessibilityProvider");
  }
  return context;
}
