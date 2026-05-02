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
  const router = useRouter();

  useEffect(() => {
    // Vérifier si le navigateur supporte la reconnaissance vocale
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      console.warn("La reconnaissance vocale n'est pas supportée par ce navigateur.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = 'en-US'; // Vous pouvez mettre 'fr-FR' si vous préférez

    recognition.onresult = (event: any) => {
      const transcript = event.results[event.results.length - 1][0].transcript.toLowerCase().trim();
      console.log("Commande vocale entendue :", transcript);

      // Chercher si le transcript contient un de nos mots-clés
      for (const [command, path] of Object.entries(COMMANDS)) {
        if (transcript.includes(command)) {
          toast.success(`Navigation vers : ${command}`, {
            description: "Commande vocale reconnue",
          });
          router.navigate({ to: path as any });
          break;
        }
      }
    };

    recognition.onerror = (event: any) => {
      console.error("Erreur reconnaissance vocale :", event.error);
      setIsListening(false);
    };

    if (isListening) {
      recognition.start();
    }

    return () => {
      recognition.stop();
    };
  }, [isListening, router]);

  return (
    <div className="fixed bottom-6 right-6 z-[100]">
      <button
        onClick={() => setIsListening(!isListening)}
        className={`flex h-12 w-12 items-center justify-center rounded-full shadow-2xl transition-all hover:scale-110 active:scale-95 ${
          isListening 
            ? "bg-red-500 text-white animate-pulse" 
            : "bg-[var(--gradient-primary)] text-white glow-purple"
        }`}
        title={isListening ? "Stop Voice Commands" : "Start Voice Commands"}
      >
        {isListening ? <Mic className="h-5 w-5" /> : <MicOff className="h-5 w-5 opacity-80" />}
      </button>
      {isListening && (
        <div className="absolute bottom-full mb-3 right-0 glass px-3 py-1.5 rounded-lg text-[10px] whitespace-nowrap gold-text font-medium border border-secondary/30 animate-in fade-in slide-in-from-bottom-2">
          Listening for commands (e.g., "Forecast")...
        </div>
      )}
    </div>
  );
}
