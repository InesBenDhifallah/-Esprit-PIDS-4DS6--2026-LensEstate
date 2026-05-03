import { Link, createFileRoute } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { Upload, Sparkles, Image as ImageIcon, Loader2, LogIn } from "lucide-react";
import { useState, useEffect } from "react";
import { SiteHeader } from "@/components/SiteHeader";
import { generate3DView } from "@/lib/ai.action";
import { ReactCompareSlider, ReactCompareSliderImage } from 'react-compare-slider';
import puter from "@heyputer/puter.js";

export const Route = createFileRoute("/visualizer")({
  head: () => ({
    meta: [
      { title: "3D Visualizer — LensEstate" },
      { name: "description", content: "Transform 2D floor plans into photorealistic 3D renders." },
    ],
  }),
  component: VisualizerPage,
});

function VisualizerPage() {
  const [sourceImage, setSourceImage] = useState<string | null>(null);
  const [renderedImage, setRenderedImage] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPuterAuthenticated, setIsPuterAuthenticated] = useState(false);

  useEffect(() => {
    // Vérifier si déjà connecté à Puter
    setIsPuterAuthenticated(puter.auth.isSignedIn());
  }, []);

  const handlePuterLogin = async () => {
    try {
      await puter.auth.signIn();
      setIsPuterAuthenticated(true);
      setError(null);
    } catch (err) {
      setError("Échec de la connexion à Puter.");
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setSourceImage(reader.result as string);
        setRenderedImage(null);
        setError(null);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleGenerate = async () => {
    if (!sourceImage) return;
    
    if (!puter.auth.isSignedIn()) {
      setError("Veuillez vous connecter à Puter.js d'abord.");
      return;
    }

    setIsProcessing(true);
    setError(null);
    try {
      const result = await generate3DView({ sourceImage });
      if (result.renderedImage) {
        setRenderedImage(result.renderedImage);
      } else {
        setError("L'IA a répondu mais n'a pas pu générer l'image. Vérifiez votre quota Puter.");
      }
    } catch (err: any) {
      console.error("Failed to generate 3D view:", err);
      setError(err.message || "Erreur de connexion avec l'IA.");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="min-h-screen">
      <SiteHeader />
      <div className="mx-auto max-w-7xl px-6 py-12">
        <div className="text-center max-w-2xl mx-auto">
          <span className="text-xs uppercase tracking-widest gold-text font-semibold">Vision AI</span>
          <h1 className="mt-2 text-4xl md:text-5xl font-bold">3D Visualizer</h1>
          <p className="mt-3 text-muted-foreground">Upload a 2D floor plan and watch it become a photorealistic 3D render.</p>
        </div>

        <div className="mt-12 grid lg:grid-cols-2 gap-8">
          <div className="space-y-6">
            <div className="rounded-2xl glass p-6">
              <h3 className="font-semibold mb-3">Upload 2D Plan</h3>
              <label className={`flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-border bg-surface/40 px-6 py-12 cursor-pointer hover:border-secondary transition \${sourceImage ? 'border-secondary bg-secondary/5' : ''}`}>
                {sourceImage ? (
                  <img src={sourceImage} alt="Source" className="max-h-48 rounded-lg shadow-lg" />
                ) : (
                  <>
                    <Upload className="h-8 w-8 text-muted-foreground" />
                    <div className="mt-3 text-sm">Drag & drop or click to upload</div>
                    <div className="text-xs text-muted-foreground mt-1">PNG, JPG up to 10MB</div>
                  </>
                )}
                <input type="file" className="hidden" onChange={handleFileUpload} accept="image/*" />
              </label>
            </div>

            <div className="rounded-2xl glass p-6">
              <h3 className="font-semibold mb-3">Puter.js Connection</h3>
              {isPuterAuthenticated ? (
                <div className="flex items-center gap-2 text-green-500 text-sm">
                  <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                  Connected to Puter Cloud
                </div>
              ) : (
                <button
                  onClick={handlePuterLogin}
                  className="w-full rounded-xl border border-secondary/50 bg-secondary/10 py-3 text-sm font-medium gold-text flex items-center justify-center gap-2 hover:bg-secondary/20 transition"
                >
                  <LogIn className="h-4 w-4" /> Connect to Puter.js
                </button>
              )}
            </div>

            <button
              onClick={handleGenerate}
              disabled={!sourceImage || isProcessing || !isPuterAuthenticated}
              className="w-full rounded-xl bg-[var(--gradient-primary)] py-4 text-sm font-semibold text-white glow-purple inline-flex items-center justify-center gap-2 hover:scale-[1.02] active:scale-95 disabled:opacity-50 disabled:scale-100 transition shadow-xl"
            >
              {isProcessing ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" /> Processing with Gemini...
                </>
              ) : (
                <>
                  <Sparkles className="h-5 w-5" /> Transform to 3D Render
                </>
              )}
            </button>

            {error && (
              <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm text-center">
                {error}
              </div>
            )}
          </div>

          <div className="rounded-2xl glass p-6 min-h-[500px] flex items-center justify-center overflow-hidden border border-white/10">
            {!renderedImage ? (
              <div className="text-center text-muted-foreground">
                {isProcessing ? (
                  <div className="flex flex-col items-center gap-4">
                    <div className="relative h-20 w-20">
                        <div className="absolute inset-0 rounded-full border-4 border-secondary/20"></div>
                        <div className="absolute inset-0 rounded-full border-4 border-secondary border-t-transparent animate-spin"></div>
                    </div>
                    <p className="animate-pulse">Building your 3D world...</p>
                  </div>
                ) : (
                  <>
                    <ImageIcon className="h-12 w-12 mx-auto opacity-40" />
                    <p className="mt-3 text-sm">Your 3D render will appear here</p>
                  </>
                )}
              </div>
            ) : (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="w-full h-full rounded-lg overflow-hidden shadow-2xl"
              >
                <ReactCompareSlider
                  itemOne={<ReactCompareSliderImage src={sourceImage!} alt="2D Plan" />}
                  itemTwo={<ReactCompareSliderImage src={renderedImage} alt="3D Render" />}
                  className="w-full h-full"
                />
              </motion.div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
