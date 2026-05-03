import { createFileRoute, Link } from "@tanstack/react-router";
import { motion, AnimatePresence } from "framer-motion";
import { useState, useRef, useEffect } from "react";
import {
  MapPin, Home, BedDouble, Bath, Maximize2, ChevronDown,
  Sparkles, ArrowRight, CheckCircle2, Building2,
  Car, Trees, Waves, Wind, ShieldCheck, Sofa, Eye, Layers,
  Thermometer, Search, Globe2, Lock, X
} from "lucide-react";
import { SiteHeader } from "@/components/SiteHeader";
import { useAuth } from "@/context/AuthContext";
import { post } from "@/lib/api";

// ─── i18n ────────────────────────────────────────────────────────────────────
const T = {
  fr: {
    dir: "ltr",
    badge: "Estimation Immobilière IA",
    h1: "Estimez votre bien",
    sub: "Obtenez une estimation précise en quelques secondes.",
    lang: "AR",
    unlockTitle: "Connectez-vous pour déverrouiller",
    unlockSub: "Inscrivez-vous pour utiliser l'estimation IA et obtenir des résultats précis.",
    signIn: "Se connecter",
    signUp: "Créer un compte",
    sections: {
      location: "Localisation",
      property: "Caractéristiques",
      amenities: "Équipements",
      description: "Description (optionnel)",
    },
    labels: {
      governorate: "Gouvernorat",
      city: "Ville ou quartier",
      cityPh: "Rechercher une ville...",
      type: "Type de bien",
      seller: "Vendeur",
      surface: "Surface (m²)",
      rooms: "Pièces",
      beds: "Chambres",
      baths: "Salles de bain",
      descPh: "Décrivez le bien (vue, état, standing...)",
    },
    types: ["Appartement", "Villa", "Studio", "Penthouse", "Maison", "Terrain"],
    sellers: ["Particulier", "Agence", "Promoteur"],
    amenities: ["Piscine", "Parking", "Jardin", "Ascenseur", "Climatisation", "Chauffage", "Sécurité", "Meublé", "Terrasse", "Vue mer", "Sous-sol", "Haut standing"],
    cta: "Estimer le prix",
    loading: "L'IA analyse votre bien...",
    resultTitle: "Estimation du bien",
    confidence: "Indice de confiance",
    trend: "Tendance du marché",
    perM2: "/m²",
    reset: "Nouvelle estimation",
    emptyTitle: "Votre estimation apparaîtra ici",
    emptySub: "Remplissez le formulaire pour commencer",
    photo: "Ajouter une photo",
    photoSub: "Améliore la précision",
  },
  ar: {
    dir: "rtl",
    badge: "تقدير العقارات بالذكاء الاصطناعي",
    h1: "قيّم عقارك",
    sub: "احصل على تقدير دقيق في ثوانٍ.",
    lang: "FR",
    unlockTitle: "سجل الدخول لفتح الميزة",
    unlockSub: "سجل الآن لاستخدام تقدير الذكاء الاصطناعي والحصول على نتائج دقيقة.",
    signIn: "تسجيل الدخول",
    signUp: "إنشاء حساب",
    sections: {
      location: "الموقع",
      property: "خصائص العقار",
      amenities: "المرافق",
      description: "وصف (اختياري)",
    },
    labels: {
      governorate: "الولاية",
      city: "المدينة أو الحي",
      cityPh: "ابحث عن مدينة...",
      type: "نوع العقار",
      seller: "البائع",
      surface: "المساحة (م²)",
      rooms: "الغرف",
      beds: "غرف النوم",
      baths: "دورات المياه",
      descPh: "صف العقار (الإطلالة، الحالة، المستوى...)",
    },
    types: ["شقة", "فيلا", "استوديو", "بنتهاوس", "منزل", "أرض"],
    sellers: ["فرد", "وكالة", "مطوّر"],
    amenities: ["مسبح", "موقف سيارات", "حديقة", "مصعد", "تكييف", "تدفئة", "أمن", "مفروشة", "تراس", "إطلالة بحرية", "قبو", "فاخر"],
    cta: "تقدير السعر",
    loading: "الذكاء الاصطناعي يحلّل عقارك...",
    resultTitle: "تقدير العقار",
    confidence: "مستوى الثقة",
    trend: "اتجاه السوق",
    perM2: "/م²",
    reset: "تقدير جديد",
    emptyTitle: "ستظهر نتيjتك هنا",
    emptySub: "أكمل النموذج للبدء",
    photo: "إضافة صورة",
    photoSub: "يحسّن الدقة",
  },
} as const;

type Lang = "fr" | "ar";
type PredictionResult = {
  price: number;
  conf: number;
  input_completeness?: number;
  location_factor_applied?: number;
  data_quality?: "high" | "medium" | "low";
  model?: string;
  input_summary?: {
    governorate: string;
    city: string;
    surface_m2: number;
    rooms: number;
    bedrooms: number;
    bathrooms: number;
    has_image: boolean;
    description_length: number;
  };
  notes?: string[];
};

const GOVS = [
  "Tunis", "Sfax", "Sousse", "Hammamet", "Nabeul", "Bizerte", "Monastir",
  "Ariana", "Ben Arous", "La Marsa", "Manouba", "Zaghouan", "Béja", "Jendouba",
  "Kef", "Siliana", "Kairouan", "Kasserine", "Sidi Bouzid", "Gabès", "Médenine",
  "Tataouine", "Gafsa", "Tozeur", "Kébili",
];

const CITIES: Record<string, string[]> = {
  Tunis: ["Tunis Centre", "La Marsa", "Sidi Bou Saïd", "Carthage", "El Menzah", "Ennasr", "Manar"],
  Sfax: ["Sfax Centre", "Sakiet Ezzit", "Thyna", "Chihia"],
  Sousse: ["Sousse Centre", "Hammam Sousse", "Kalia", "Khezama"],
  Hammamet: ["Hammamet Nord", "Hammamet Sud", "Nabeul"],
};

const AMENITY_KEYS = [
  "has_pool", "has_parking", "has_garden", "has_elevator",
  "has_air_conditioning", "has_heating", "has_security", "has_furniture",
  "has_terrace", "has_sea_view", "has_basement", "has_standing",
];

// ─── Component ────────────────────────────────────────────────────────────────
export const Route = createFileRoute("/price-prediction")({
  head: () => ({ meta: [{ title: "Estimation — LensEstate" }] }),
  component: PredictPage,
});

function PredictPage() {
  const { isAuthenticated } = useAuth();
  const [lang, setLang] = useState<Lang>("fr");
  const t = T[lang];

  const [form, setForm] = useState({
    region: "Tunis", city: "", property_type: "appartement", seller_type: "particulier",
    surface_m2: 120, rooms: 4, bedrooms: 3, bathrooms: 2, description: "",
    has_pool: false, has_parking: false, has_garden: false, has_elevator: false,
    has_air_conditioning: false, has_heating: false, has_security: false,
    has_furniture: false, has_terrace: false, has_sea_view: false,
    has_basement: false, has_standing: false,
  });

  const [citySearch, setCitySearch] = useState("");
  const [showCitySugg, setShowCitySugg] = useState(false);
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const imageRef = useRef<HTMLInputElement>(null);
  const [imagePreviews, setImagePreviews] = useState<string[]>([]);
  const [images, setImages] = useState<File[]>([]);

  const citySuggestions = [
    ...(CITIES[form.region] || []),
    ...GOVS.filter(g => g !== form.region),
  ].filter(c => c.toLowerCase().includes(citySearch.toLowerCase())).slice(0, 6);

  const set = (k: string, v: unknown) => setForm(f => ({ ...f, [k]: v }));
  const canPredict =
    form.surface_m2 >= 10 &&
    form.rooms >= 0 &&
    form.bedrooms >= 0 &&
    form.bathrooms >= 0 &&
    form.region.trim().length > 0 &&
    (form.city.trim().length > 0 || form.region.trim().length > 0);

  const predict = async () => {
    setLoading(true); setError(null);
    try {
      const fd = new FormData();
      fd.append("region", form.region);
      fd.append("city", form.city || form.region);
      fd.append("property_type", form.property_type);
      fd.append("seller_type", form.seller_type);
      fd.append("surface_m2", String(form.surface_m2));
      fd.append("rooms", String(form.rooms));
      fd.append("bedrooms", String(form.bedrooms));
      fd.append("bathrooms", String(form.bathrooms));
      fd.append("description", form.description.trim());
      fd.append("image_count", String(images.length));
      AMENITY_KEYS.forEach(k => fd.append(k, String((form as any)[k])));
      if (images.length > 0) fd.append("image", images[0]);

      const data = await post<PredictionResult>("/api/predict/", fd);
      setResult(data);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const amenityCount = AMENITY_KEYS.filter(k => (form as any)[k]).length;

  return (
    <div className="min-h-screen bg-background" dir={t.dir}>
      <SiteHeader />

      {/* Lang toggle */}
      <div className={`fixed top-20 z-50 ${lang === "ar" ? "left-4" : "right-4"}`}>
        <button
          onClick={() => setLang(l => l === "fr" ? "ar" : "fr")}
          className="flex items-center gap-1.5 rounded-full border border-border bg-surface/80 px-3 py-1.5 text-xs font-semibold backdrop-blur shadow-sm hover:border-primary/50 transition-colors"
        >
          <Globe2 className="h-3.5 w-3.5" />{t.lang}
        </button>
      </div>

      <div className="mx-auto max-w-5xl px-4 sm:px-6 py-10">
        {/* Hero */}
        <div className="text-center mb-10 space-y-3">
          <span className="inline-block rounded-full bg-primary/10 border border-primary/20 px-4 py-1 text-xs font-semibold text-primary">
            {t.badge}
          </span>
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight">{t.h1}</h1>
          <p className="text-muted-foreground max-w-md mx-auto text-sm">{t.sub}</p>
        </div>

        <div className="grid lg:grid-cols-[1fr_360px] gap-6">
          {/* ═══ LEFT: Form ═══ */}
          <div className="space-y-4">

            {/* Location */}
            <Card title={t.sections.location} icon={<MapPin className="h-4 w-4" />}>
              <div className="grid sm:grid-cols-2 gap-3">
                <Field label={t.labels.governorate}>
                  <div className="relative">
                    <select
                      value={form.region}
                      onChange={e => { 
                        set("region", e.target.value); 
                        set("city", ""); 
                        setCitySearch(""); 
                      }}
                      className="inp pr-8"
                    >
                      {GOVS.map(g => <option key={g}>{g}</option>)}
                    </select>
                    <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                  </div>
                </Field>
                <Field label={t.labels.city}>
                  <div className="relative group">
                    <Search className={`absolute ${lang === "ar" ? "right-3" : "left-3"} top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none transition-colors group-focus-within:text-primary`} />
                    <input
                      value={citySearch}
                      onChange={e => { setCitySearch(e.target.value); set("city", e.target.value); setShowCitySugg(true); }}
                      onFocus={() => setShowCitySugg(true)}
                      onBlur={() => setTimeout(() => setShowCitySugg(false), 150)}
                      placeholder={t.labels.cityPh}
                      className={`inp ${lang === "ar" ? "pr-9 pl-9" : "pl-9 pr-9"}`}
                    />
                    {citySearch && (
                      <button
                        onClick={() => { setCitySearch(""); set("city", ""); }}
                        className={`absolute ${lang === "ar" ? "left-2" : "right-2"} top-1/2 -translate-y-1/2 p-1 hover:bg-muted rounded-full transition-colors`}
                      >
                        <X className="h-3 w-3 text-muted-foreground" />
                      </button>
                    )}
                    {showCitySugg && citySuggestions.length > 0 && (
                      <div className="absolute top-full left-0 right-0 mt-1 z-10 rounded-xl border border-border bg-surface overflow-hidden">
                        {citySuggestions.map((c, i) => (
                          <button key={c} type="button"
                            onMouseDown={() => { setCitySearch(c); set("city", c); setShowCitySugg(false); }}
                            className={`w-full px-4 py-2 text-left text-sm transition-colors ${i === 0
                                ? "bg-primary/10 font-semibold text-primary"
                                : "hover:bg-primary/5"
                              }`}
                          >{c}</button>
                        ))}
                      </div>
                    )}
                  </div>
                </Field>
              </div>
            </Card>

            {/* Property */}
            <Card title={t.sections.property} icon={<Home className="h-4 w-4" />}>
              <div className="grid sm:grid-cols-2 gap-3">
                <Field label={t.labels.type}>
                  <div className="relative">
                    <select value={form.property_type} onChange={e => set("property_type", e.target.value)} className="inp pr-8">
                      {t.types.map((label, i) => (
                        <option key={i} value={["appartement", "villa", "studio", "penthouse", "maison", "terrain"][i]}>{label}</option>
                      ))}
                    </select>
                    <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                  </div>
                </Field>
                <Field label={t.labels.seller}>
                  <div className="relative">
                    <select value={form.seller_type} onChange={e => set("seller_type", e.target.value)} className="inp pr-8">
                      {t.sellers.map((s, i) => (
                        <option key={i} value={["particulier", "agence", "promoteur"][i]}>{s}</option>
                      ))}
                    </select>
                    <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                  </div>
                </Field>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-1">
                {[
                  { label: t.labels.surface, key: "surface_m2", icon: <Maximize2 className="h-3 w-3" />, min: 10, max: 10000 },
                  { label: t.labels.rooms, key: "rooms", icon: <Building2 className="h-3 w-3" />, min: 0, max: 42 },
                  { label: t.labels.beds, key: "bedrooms", icon: <BedDouble className="h-3 w-3" />, min: 0, max: 20 },
                  { label: t.labels.baths, key: "bathrooms", icon: <Bath className="h-3 w-3" />, min: 0, max: 15 },
                ].map(({ label, key, icon, min, max }) => (
                  <Field key={key} label={label} icon={icon}>
                    <input type="number" min={min} max={max}
                      value={(form as any)[key]}
                      onChange={e => set(key, Number(e.target.value))}
                      className="inp text-center font-semibold" />
                  </Field>
                ))}
              </div>
            </Card>

            {/* Amenities */}
            <Card title={`${t.sections.amenities}${amenityCount > 0 ? ` (${amenityCount})` : ""}`} icon={<CheckCircle2 className="h-4 w-4" />}>
              <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
                {AMENITY_KEYS.map((key, i) => {
                  const icons = [<Waves />, <Car />, <Trees />, <Layers />, <Wind />, <Thermometer />, <ShieldCheck />, <Sofa />, <Home />, <Eye />, <Building2 />, <Sparkles />];
                  const active = (form as any)[key];
                  return (
                    <button key={key} type="button" onClick={() => set(key, !active)}
                      className={`flex flex-col items-center gap-1 rounded-xl border p-2.5 text-[11px] font-medium transition-all ${active ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground hover:border-primary/30"
                        }`}
                    >
                      <span className="h-4 w-4 [&>svg]:h-4 [&>svg]:w-4">{icons[i]}</span>
                      {t.amenities[i]}
                    </button>
                  );
                })}
              </div>
            </Card>

            {/* Description + Photo */}
            <Card title={t.sections.description} icon={<Eye className="h-4 w-4" />}>
              <textarea value={form.description}
                onChange={e => set("description", e.target.value)}
                placeholder={t.labels.descPh}
                rows={3} className="inp resize-none" />

              <div className="mt-3 space-y-3">
                <input type="file" ref={imageRef} multiple accept="image/*" className="hidden"
                  onChange={e => {
                    const files = Array.from(e.target.files || []);
                    setImages(files);
                    setImagePreviews(files.map(f => URL.createObjectURL(f)));
                  }}
                />

                <button
                  type="button"
                  onClick={() => imageRef.current?.click()}
                  className="w-full flex items-center justify-center gap-3 rounded-xl border border-dashed border-border hover:border-primary/40 p-4 transition-colors group"
                >
                  <div className="h-10 w-10 rounded-full bg-primary/5 flex items-center justify-center group-hover:bg-primary/10 transition-colors">
                    <MapPin className="h-5 w-5 text-primary" />
                  </div>
                  <div className="text-left">
                    <div className="text-sm font-semibold">{t.photo}</div>
                    <div className="text-xs text-muted-foreground">{t.photoSub}</div>
                  </div>
                </button>

                {imagePreviews.length > 0 && (
                  <div className="grid grid-cols-4 gap-2">
                    {imagePreviews.map((url, i) => (
                      <div key={i} className="relative aspect-video rounded-lg overflow-hidden border border-border">
                        <img src={url} alt="" className="h-full w-full object-cover" />
                        {i === 0 && (
                          <div className="absolute top-1 left-1 bg-primary text-[10px] text-white px-1.5 py-0.5 rounded-md font-bold uppercase">IA</div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </Card>

            {error && (
              <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
                ⚠️ {error}
              </div>
            )}

            {/* Submit / Auth CTA */}
            {!isAuthenticated ? (
              <div className="rounded-2xl bg-primary/5 border border-primary/20 p-6 text-center space-y-4">
                <div className="mx-auto h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                  <Lock className="h-6 w-6 text-primary" />
                </div>
                <div>
                  <h3 className="font-bold text-lg">{t.unlockTitle}</h3>
                  <p className="text-sm text-muted-foreground mt-1">{t.unlockSub}</p>
                </div>
                <div className="grid grid-cols-2 gap-3 pt-2">
                  <Link to={"/auth" as any} className="rounded-xl border border-primary/30 py-2.5 text-sm font-semibold text-primary hover:bg-primary/5 transition-all">
                    {t.signIn}
                  </Link>
                  <Link to={"/auth" as any} className="rounded-xl bg-primary py-2.5 text-sm font-semibold text-white hover:opacity-90 transition-all">
                    {t.signUp}
                  </Link>
                </div>
              </div>
            ) : (
              <button onClick={predict} disabled={loading || !canPredict}
                className="w-full rounded-2xl py-4 font-bold text-white flex items-center justify-center gap-2 disabled:opacity-60 transition-all active:scale-[.98]"
                style={{ background: "var(--gradient-primary)" }}
              >
                {loading
                  ? <><div className="h-4 w-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />{t.loading}</>
                  : <><Sparkles className="h-4 w-4" />{t.cta}<ArrowRight className="h-4 w-4" /></>
                }
              </button>
            )}
          </div>

          {/* ═══ RIGHT: Result ═══ */}
          <div className="lg:sticky lg:top-24 h-fit">
            <AnimatePresence mode="wait">
              {result ? (
                <motion.div key="result"
                  initial={{ opacity: 0, y: 16, scale: 0.97 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  className="rounded-2xl overflow-hidden"
                >
                  <div className="p-6 text-white" style={{ background: "var(--gradient-primary)" }}>
                    <div className="text-xs uppercase tracking-widest text-white/60 mb-3">{t.resultTitle}</div>
                    <div className="text-5xl font-bold leading-none">
                      {result.price.toLocaleString("fr-TN", { maximumFractionDigits: 0 })}
                    </div>
                    <div className="text-xl text-white/70 mt-1">TND</div>
                    <div className="text-sm text-white/50 mt-1">
                      {Math.round(result.price / form.surface_m2).toLocaleString()} TND{t.perM2}
                    </div>
                  </div>

                  <div className="bg-surface/80 p-4 border border-border/50 rounded-b-2xl space-y-2">
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div className="rounded-lg border border-border/60 px-3 py-2">
                        <div className="text-xs text-muted-foreground">{t.confidence}</div>
                        <div className="font-semibold">{result.conf}%</div>
                      </div>
                      <div className="rounded-lg border border-border/60 px-3 py-2">
                        <div className="text-xs text-muted-foreground">Data quality</div>
                        <div className="font-semibold">{result.data_quality ?? "n/a"}</div>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div className="rounded-lg border border-border/60 px-3 py-2">
                        <div className="text-xs text-muted-foreground">Input completeness</div>
                        <div className="font-semibold">{result.input_completeness ?? 0}%</div>
                      </div>
                      <div className="rounded-lg border border-border/60 px-3 py-2">
                        <div className="text-xs text-muted-foreground">Location impact</div>
                        <div className="font-semibold">
                          {result.location_factor_applied
                            ? `${Math.round((result.location_factor_applied - 1) * 100)}%`
                            : "0%"}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <MapPin className="h-4 w-4 text-primary" />
                      <span>{form.city || form.region}, {form.region}</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <Maximize2 className="h-4 w-4 text-primary" />
                      <span>{form.surface_m2} m² · {form.bedrooms} ch. · {form.bathrooms} sdb</span>
                    </div>
                    {amenityCount > 0 && (
                      <div className="flex items-center gap-2 text-sm">
                        <CheckCircle2 className="h-4 w-4 text-primary" />
                        <span>{amenityCount} équipements</span>
                      </div>
                    )}
                    {(result.notes?.length ?? 0) > 0 && (
                      <div className="rounded-lg bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
                        {result.notes!.join(" ")}
                      </div>
                    )}
                    {result.input_summary && (
                      <div className="rounded-lg bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
                        Inputs used: {result.input_summary.city}, {result.input_summary.governorate} · {result.input_summary.surface_m2} m² · {result.input_summary.rooms} rooms · image: {result.input_summary.has_image ? "yes" : "no"}
                      </div>
                    )}
                    <button onClick={() => { setResult(null); setError(null); }}
                      className="mt-3 w-full rounded-xl border border-border py-2 text-sm text-muted-foreground hover:text-foreground hover:border-primary/50 transition-colors"
                    >{t.reset}</button>
                  </div>
                </motion.div>
              ) : (
                <motion.div key="empty"
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  className="rounded-2xl border border-dashed border-border/60 flex flex-col items-center justify-center p-10 min-h-[340px] gap-4 text-center"
                >
                  <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
                    <Sparkles className="h-7 w-7 text-primary" />
                  </div>
                  <div>
                    <p className="font-semibold">{t.emptyTitle}</p>
                    <p className="text-sm text-muted-foreground mt-1">{t.emptySub}</p>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      <style>{`
        .inp {
          width: 100%;
          border-radius: 0.75rem;
          border: 1.5px solid var(--border);
          background: color-mix(in oklab, var(--surface) 60%, transparent);
          padding: .625rem 1rem;
          font-size: .875rem;
          outline: none;
          transition: border-color .2s;
          color: inherit;
          appearance: none;
          box-shadow: none !important;
        }
        .inp:focus {
          border-color: hsl(var(--primary));
          box-shadow: none !important;
        }
      `}</style>
    </div>
  );
}

function Card({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-border/60 bg-surface/80 p-5 space-y-4">
      <div className="flex items-center gap-2 text-sm font-semibold">
        <span className="text-primary">{icon}</span>{title}
      </div>
      {children}
    </div>
  );
}

function Field({ label, icon, children }: { label: string; icon?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="flex items-center gap-1 text-xs text-muted-foreground font-medium">
        {icon && <span>{icon}</span>}{label}
      </label>
      {children}
    </div>
  );
}
