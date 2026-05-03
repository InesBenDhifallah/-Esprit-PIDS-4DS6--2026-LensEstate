import { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Link } from "@tanstack/react-router";

export type MapProperty = {
  id: string;
  title: string;
  price: number | null;
  region: string;
  image: string;
  lat: number;
  lng: number;
};

const makeIcon = (selected: boolean) =>
  L.divIcon({
    className: "lens-marker",
    html: `<div class="lens-pin ${selected ? "lens-pin-selected" : ""}">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0"/><circle cx="12" cy="10" r="3"/></svg>
    </div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -30],
  });

function FlyTo({ lat, lng }: { lat: number; lng: number }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo([lat, lng], Math.max(map.getZoom(), 9), { duration: 0.8 });
  }, [lat, lng, map]);
  return null;
}

export function TunisiaMap({
  properties,
  selected,
  onSelect,
}: {
  properties: MapProperty[];
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  const groups = properties.reduce<
    Record<string, { lat: number; lng: number; items: MapProperty[] }>
  >((acc, property) => {
    const key = `${property.lat},${property.lng}`;
    if (!acc[key]) {
      acc[key] = { lat: property.lat, lng: property.lng, items: [] };
    }
    acc[key].items.push(property);
    return acc;
  }, {});

  const groupedProperties = Object.values(groups);
  const active = properties.find((p) => p.id === selected);

  return (
    <MapContainer
      center={[34.0, 9.5]}
      zoom={6}
      scrollWheelZoom
      className="h-full w-full"
      style={{ background: "hsl(240 10% 6%)" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      />
      {groupedProperties.map((group) => (
        <Marker
          key={`${group.lat}-${group.lng}`}
          position={[group.lat, group.lng]}
          icon={makeIcon(group.items.some((item) => item.id === selected))}
          eventHandlers={{
            click: () => {
              if (group.items[0]) onSelect(group.items[0].id);
            },
          }}
        >
          <Popup className="lens-popup">
            <div className="w-56 space-y-3">
              {group.items.map((p) => (
                <div key={p.id} className="border-b border-border pb-3 last:border-0 last:pb-0">
                  <img
                    src={p.image}
                    alt={p.title}
                    className="h-24 w-full rounded-lg object-cover"
                  />
                  <div className="mt-2 text-sm font-medium text-foreground">{p.title}</div>
                  <div className="text-xs text-muted-foreground">{p.region}</div>
                  <div className="mt-1 font-semibold gold-text">
                    {p.price === null ? "Price on request" : `${p.price.toLocaleString()} TND`}
                  </div>
                  <Link
                    to="/property/$id"
                    params={{ id: p.id }}
                    className="mt-2 inline-block text-xs gold-text"
                  >
                    View details →
                  </Link>
                </div>
              ))}
            </div>
          </Popup>
        </Marker>
      ))}
      {active && <FlyTo lat={active.lat} lng={active.lng} />}
    </MapContainer>
  );
}

export default TunisiaMap;
