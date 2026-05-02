import { useEffect, useState } from "react";
import { useRouter } from "@tanstack/react-router";
import { Mic, MicOff } from "lucide-react";
import { toast } from "sonner";

const COMMANDS: Record<string, string> = {
  "home": "/",
  "accueil": "/",
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
  const [isListening, setIsListening] = useState(false);
  const [lastTranscript, setLastTranscript] = useState("");
  const router = useRouter();

  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      console.warn("La reconnaissance vocale n'est pas supportée par ce navigateur.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true; // Pour voir le texte en temps réel
    recognition.lang = 'fr-FR'; // On met en français par défaut ou auto

    recognition.onresult = (event: any) => {
      const transcript = event.results[event.results.length - 1][0].transcript.toLowerCase().trim();
      setLastTranscript(transcript);
      console.log("Entendu :", transcript);

      if (event.results[event.results.length - 1].isFinal) {
        for (const [command, path] of Object.entries(COMMANDS)) {
          if (transcript.includes(command)) {
            toast.success(`Navigation : ${command}`, {
                icon: "🚀",
            });
            router.navigate({ to: path as any });
            setLastTranscript("");
            break;
          }
        }
      }
    };

    recognition.onerror = (event: any) => {
      console.error("Erreur Speech:", event.error);
      setIsListening(false);
    };

    if (isListening) {
      try {
        recognition.start();
      } catch (e) {
        console.error("Start error:", e);
      }
    }

    return () => {
      recognition.stop();
    };
  }, [isListening, router]);

  return (
    <div className="fixed bottom-6 right-6 z-[100] flex flex-col items-end gap-3">
      {lastTranscript && isListening && (
        <div className="glass px-4 py-2 rounded-2xl text-xs gold-text border border-secondary/30 animate-pulse max-w-[200px] text-center shadow-2xl">
           " {lastTranscript} "
        </div>
      )}
      <div className="relative">
        <button
          onClick={() => setIsListening(!isListening)}
          className={`flex h-14 w-14 items-center justify-center rounded-full shadow-2xl transition-all hover:scale-110 active:scale-95 ${
            isListening 
              ? "bg-red-500 text-white animate-pulse" 
              : "bg-[var(--gradient-primary)] text-white glow-purple"
          }`}
        >
          {isListening ? <Mic className="h-6 w-6" /> : <MicOff className="h-6 w-6 opacity-80" />}
        </button>
      </div>
    </div>
  );
}
