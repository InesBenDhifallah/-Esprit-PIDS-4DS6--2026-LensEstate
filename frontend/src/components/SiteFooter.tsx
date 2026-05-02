import { Link } from "@tanstack/react-router";
import { Sparkles } from "lucide-react";

export function SiteFooter() {
  return (
    <footer className="border-t border-border mt-24">
      <div className="mx-auto max-w-7xl px-6 py-12 grid gap-8 md:grid-cols-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--gradient-primary)]">
              <Sparkles className="h-4 w-4 text-white" />
            </span>
            <span className="font-semibold">Lens<span className="gold-text">Estate</span></span>
          </div>
          <p className="mt-3 text-sm text-muted-foreground max-w-xs">
            AI-powered real estate intelligence for transparent, data-driven property decisions.
          </p>
        </div>
        <div>
          <h4 className="text-sm font-semibold mb-3">Product</h4>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li><Link to="/map">Explore Map</Link></li>
            <li><Link to="/price-prediction">Price Prediction</Link></li>
            <li><Link to="/forecasting">Forecasting</Link></li>
            <li><Link to="/plan-generator">2D Plans</Link></li>
          </ul>
        </div>
        <div>
          <h4 className="text-sm font-semibold mb-3">Company</h4>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li>About</li><li>Blog</li><li>Careers</li><li>Press</li>
          </ul>
        </div>
        <div>
          <h4 className="text-sm font-semibold mb-3">Legal</h4>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li>Privacy</li><li>Terms</li><li>Cookies</li>
          </ul>
        </div>
      </div>
      <div className="border-t border-border py-6 text-center text-xs text-muted-foreground">
        © {new Date().getFullYear()} LensEstate. All rights reserved.
      </div>
    </footer>
  );
}
