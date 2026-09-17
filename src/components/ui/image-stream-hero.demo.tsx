// This is a file with a demo for your component
// That's what users will see in the preview
// Create new files in this directory to add more demos

import { ImageStreamHero } from "@/components/ui/image-stream-hero";

const IMAGES = [
  {
    src: "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=800&q=80&auto=format&fit=crop",
    alt: "Misty mountain valley at sunrise",
  },
  {
    src: "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=800&q=80&auto=format&fit=crop",
    alt: "Rocky mountain range under a clear sky",
  },
  {
    src: "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?w=800&q=80&auto=format&fit=crop",
    alt: "Alpine lake reflecting snow-capped peaks",
  },
  {
    src: "https://images.unsplash.com/photo-1519681393784-d120267933ba?w=800&q=80&auto=format&fit=crop",
    alt: "Layered mountain ridgelines fading into haze",
  },
  {
    src: "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800&q=80&auto=format&fit=crop",
    alt: "Sunlight breaking through a dense forest canopy",
  },
  {
    src: "https://images.unsplash.com/photo-1447752875215-b2761acb3c5d?w=800&q=80&auto=format&fit=crop",
    alt: "Snow-dusted mountain range at dusk",
  },
  {
    src: "https://images.unsplash.com/photo-1426604966848-d7adac402bff?w=800&q=80&auto=format&fit=crop",
    alt: "Tall pine forest shrouded in fog",
  },
  {
    src: "https://images.unsplash.com/photo-1500534623283-312aade485b7?w=800&q=80&auto=format&fit=crop",
    alt: "Golden hour light over a mountain summit",
  },
  {
    src: "https://images.unsplash.com/photo-1493246507139-91e8fad9978e?w=800&q=80&auto=format&fit=crop",
    alt: "Dramatic clouds rolling over mountain peaks",
  },
  {
    src: "https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?w=800&q=80&auto=format&fit=crop",
    alt: "Wide open landscape under a pastel sky",
  },
  {
    src: "https://images.unsplash.com/photo-1501594907352-04cda38ebc29?w=800&q=80&auto=format&fit=crop",
    alt: "Sunrise breaking over distant mountain ridges",
  },
  {
    src: "https://images.unsplash.com/photo-1508739773434-c26b3d09e071?w=800&q=80&auto=format&fit=crop",
    alt: "Deep valley framed by steep mountain walls",
  },
];

// ONLY DEFAULT EXPORT WILL BE TREATED AS A DEMO
export default function ImageStreamHeroDemo() {
  return (
    <ImageStreamHero
      images={IMAGES}
      className="h-[560px] w-full rounded-lg border border-border bg-background"
    >
      <div className="relative z-10 flex h-full flex-col items-center justify-between py-12 text-center">
        <div className="px-6">
          <h1 className="text-balance text-4xl font-medium tracking-tight text-foreground sm:text-5xl">
            Your work,
            <br />
            front and centre.
          </h1>
        </div>
        <p className="max-w-md text-balance px-6 text-sm text-muted-foreground">
          A hero that leads with the images instead of describing them. Swap in
          your own and the corridor rebuilds around them.
        </p>
      </div>
    </ImageStreamHero>
  );
}
