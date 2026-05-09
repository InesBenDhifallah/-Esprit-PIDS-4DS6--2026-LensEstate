import { useEffect, useState } from "react";
import { useRouter } from "@tanstack/react-router";
import { toast } from "sonner";
import { useAccessibility } from "@/context/AccessibilityContext";

const COMMANDS: Record<string, string> = {
  "home": "/",
  "accueil": "/",
  "go home": "/",
  "retour": "/",
  "explore": "/map",
  "explorer": "/map",
  "map": "/map",
  "carte": "/map",
  "chat": "/ai-chat",
  "ai chat": "/ai-chat",
  "predict": "/price-prediction",
  "prédire": "/price-prediction",
  "forecast": "/forecasting",
  "prévision": "/forecasting",
  "plan": "/plan-generator",
  "visualizer": "/visualizer",
  "3d": "/visualizer",
};

export function VoiceNavigator() {
  const { isVoiceNavEnabled: isListening } = useAccessibility();
  const [lastTranscript, setLastTranscript] = useState("");
  const router = useRouter();

  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      console.error("CRITICAL: SpeechRecognition NOT SUPPORTED in this browser.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      console.log("VOICE: Recognition started");
    };

    recognition.onresult = (event: any) => {
      let interimTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          const transcript = event.results[i][0].transcript.toLowerCase().trim();
          console.log("VOICE FINAL:", transcript);
          setLastTranscript(transcript);

          for (const [command, path] of Object.entries(COMMANDS)) {
            if (transcript.includes(command.toLowerCase())) {
              toast.success(`Navigating to ${command}...`);
              router.navigate({ to: path as any });
              break;
            }
          }
        } else {
          interimTranscript += event.results[i][0].transcript;
        }
      }
      if (interimTranscript) {
        setLastTranscript(interimTranscript);
      }
    };

    recognition.onerror = (event: any) => {
      console.error("VOICE ERROR:", event.error);
      if (event.error === 'not-allowed') {
        alert("Microphone access denied. Please enable it in browser settings.");
      }
    };

    recognition.onend = () => {
      console.log("VOICE: Recognition ended");
      if (isListening) {
        try {
          recognition.start();
        } catch (e) {
          console.error("Restart Error:", e);
        }
      }
    };

    if (isListening) {
      try {
        recognition.start();
      } catch (e) {
        console.error("Start Error:", e);
      }
    } else {
      recognition.stop();
    }

    return () => {
      recognition.stop();
    };
  }, [isListening, router]);

  return null;
}
