import puter from "@heyputer/puter.js";

export const LENSESTATE_RENDER_PROMPT = `Transform this 2D architectural floor plan into a photorealistic, top-down 3D architectural visualization. 
The output should look like a professional 3D floor plan render with:
- Realistic textures for flooring (wood, marble, or carpet).
- Detailed 3D furniture models placed accurately based on the 2D layout.
- Soft, natural interior lighting with realistic shadows.
- Clean white or neutral walls.
- High-quality architectural rendering style.
The perspective must be strictly top-down (orthographic or slightly angled but showing the whole layout).`;

export const fetchAsDataUrl = async (url: string): Promise<string> => {
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch image: \${response.statusText}`);
  }

  const blob = await response.blob();

  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
};

interface Generate3DViewParams {
    sourceImage: string;
}

export const generate3DView = async ({ sourceImage }: Generate3DViewParams) => {
    console.log("Starting 3D generation...");
    
    try {
        const dataUrl = sourceImage.startsWith('data:')
            ? sourceImage
            : await fetchAsDataUrl(sourceImage);

        const base64Data = dataUrl.split(',')[1];
        const mimeType = dataUrl.split(';')[0].split(':')[1];

        if(!mimeType || !base64Data) throw new Error('Invalid source image payload');

        console.log("Calling Puter AI with model gemini-2.5-flash-image-preview...");
        
        // Timeout de sécurité après 60 secondes
        const response = await Promise.race([
            puter.ai.txt2img(LENSESTATE_RENDER_PROMPT, {
                provider: "gemini",
                model: "gemini-2.5-flash-image-preview",
                input_image: base64Data,
                input_image_mime_type: mimeType,
                ratio: { w: 1024, h: 1024 },
            }),
            new Promise((_, reject) => setTimeout(() => reject(new Error("Timeout: L'IA met trop de temps à répondre")), 60000))
        ]);

        console.log("Response received from Puter:", response);

        const rawImageUrl = (response as HTMLImageElement).src ?? null;

        if (!rawImageUrl) {
            console.error("No image URL in Puter response");
            return { renderedImage: null, renderedPath: undefined };
        }

        const renderedImage = rawImageUrl.startsWith('data:')
            ? rawImageUrl 
            : await fetchAsDataUrl(rawImageUrl);

        console.log("3D Generation successful!");
        return { renderedImage, renderedPath: undefined };

    } catch (error: any) {
        console.error("Error in generate3DView:", error);
        throw new Error(error.message || "Une erreur inconnue est survenue lors de la génération 3D.");
    }
}
