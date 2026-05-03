import { useEffect, useState } from "react";
import { useRouter } from "@tanstack/react-router";
import { Mic, MicOff } from "lucide-react";
import { toast } from "sonner";

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
  const [isListening, setIsListening] = useState(false);
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
    recognition.lang = 'en-US'; // On repasse en EN pour "Forecast"

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

          // Vérification des commandes
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
        setIsListening(false);
      }
    };

    recognition.onend = () => {
      console.log("VOICE: Recognition ended");
      // Relancer si on est toujours en mode "isListening"
      if (isListening) {
        recognition.start();
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

  return (
    <div className="fixed bottom-6 right-6 z-[100] flex flex-col items-end gap-3">
      {isListening && (
        <div className="glass px-4 py-3 rounded-2xl text-xs gold-text border border-secondary/30 shadow-2xl animate-pulse min-w-[150px] text-center">
          {lastTranscript ? `"${lastTranscript}"` : "Listening..."}
        </div>
      )}
      <button
        onClick={() => setIsListening(!isListening)}
        className={`flex h-14 w-14 items-center justify-center rounded-full shadow-2xl transition-all ${
          isListening 
            ? "bg-red-500 text-white scale-110 shadow-red-500/50" 
            : "bg-[var(--gradient-primary)] text-white glow-purple"
        }`}
      >
        {isListening ? <Mic className="h-6 w-6" /> : <MicOff className="h-6 w-6 opacity-80" />}
      </button>
    </div>
  );
}
