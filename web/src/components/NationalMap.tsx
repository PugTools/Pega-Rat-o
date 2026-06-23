"use client";

import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";

const alertsByState = [
  { uf: "DF", alerts: 18, position: [-15.7939, -47.8828] as [number, number] },
  { uf: "SP", alerts: 42, position: [-23.5505, -46.6333] as [number, number] },
  { uf: "RJ", alerts: 27, position: [-22.9068, -43.1729] as [number, number] },
  { uf: "BA", alerts: 21, position: [-12.9777, -38.5016] as [number, number] },
  { uf: "AM", alerts: 13, position: [-3.119, -60.0217] as [number, number] },
];

const markerIcon = L.divIcon({
  className: "ongp-map-marker",
  html: '<span class="block h-4 w-4 rounded-full border-2 border-white bg-red-600 shadow"></span>',
  iconSize: [16, 16],
  iconAnchor: [8, 8],
});

export function NationalMap() {
  return (
    <section className="mt-6 rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 px-5 py-4">
        <h3 className="text-base font-semibold text-slate-950">
          Mapa Nacional de Alertas
        </h3>
        <p className="mt-1 text-sm text-slate-500">
          Distribuicao demonstrativa por UF
        </p>
      </div>
      <div className="h-[420px] overflow-hidden rounded-b-lg">
        <MapContainer
          center={[-14.235, -51.9253]}
          className="h-full w-full"
          scrollWheelZoom={false}
          zoom={4}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {alertsByState.map((item) => (
            <Marker icon={markerIcon} key={item.uf} position={item.position}>
              <Popup>
                <strong>{item.uf}</strong>
                <br />
                {item.alerts} alertas monitorados
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </section>
  );
}
