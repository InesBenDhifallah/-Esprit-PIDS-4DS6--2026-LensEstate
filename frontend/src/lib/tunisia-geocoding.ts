const GOVERNORATE_COORDS: Record<string, [number, number]> = {
  Tunis: [36.819, 10.1658],
  Ariana: [36.8625, 10.1956],
  "Ben Arous": [36.7533, 10.2283],
  Manouba: [36.8089, 10.0975],
  Nabeul: [36.4561, 10.7376],
  Zaghouan: [36.4029, 10.1429],
  Bizerte: [37.2744, 9.8739],
  Béja: [36.7256, 9.1817],
  Jendouba: [36.5011, 8.7757],
  Kef: [36.1822, 8.7149],
  Siliana: [36.0843, 9.3708],
  Sousse: [35.8256, 10.6369],
  Monastir: [35.7643, 10.8113],
  Mahdia: [35.5047, 11.0622],
  Sfax: [34.7406, 10.7603],
  Kairouan: [35.6781, 10.0963],
  Kasserine: [35.1722, 8.8306],
  "Sidi Bouzid": [35.0382, 9.4849],
  Gabès: [33.8881, 10.0975],
  Medenine: [33.3549, 10.5055],
  Tataouine: [32.9211, 10.4518],
  Gafsa: [34.425, 8.7842],
  Tozeur: [33.9197, 8.1335],
  Kebili: [33.7042, 8.969],
};

const CITY_COORDS: Record<string, [number, number]> = {
  "La Marsa": [36.8781, 10.3242],
  "Sidi Bou Said": [36.8706, 10.3417],
  Carthage: [36.8528, 10.3233],
  Hammamet: [36.4, 10.6167],
  Nabeul: [36.4561, 10.7376],
  Sousse: [35.8256, 10.6369],
  Sfax: [34.7406, 10.7603],
  Monastir: [35.7643, 10.8113],
  Bizerte: [37.2744, 9.8739],
  Gabès: [33.8881, 10.0975],
  Djerba: [33.8075, 10.8451],
  Tozeur: [33.9197, 8.1335],
};

export function getCoords(governorate: string, city: string): [number, number] | null {
  if (city && CITY_COORDS[city]) return CITY_COORDS[city];
  if (governorate && GOVERNORATE_COORDS[governorate]) return GOVERNORATE_COORDS[governorate];
  return null;
}
