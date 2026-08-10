# flutter_app/

Frontend Flutter del sistema CENERIS Web. Consume la API Django del monorepo (raíz).

Al momento de esta reestructuración (v2), esta carpeta contiene **sólo scaffolding**: el `.gitignore` y este README. El proyecto Flutter todavía no fue inicializado; hay que hacerlo con `flutter create` (ver abajo).

---

## Bootstrap

Desde `flutter_app/`:

```bash
flutter create . --org com.ceneris --project-name ceneris_app --platforms=android,ios
```

Esto genera `pubspec.yaml`, `lib/main.dart`, `android/`, `ios/`, `test/`, etc. sin pisar los archivos existentes (`README.md`, `.gitignore`). Después, agregar plataformas adicionales si hace falta:

```bash
flutter create . --platforms=web,windows
```

Verificar:

```bash
flutter pub get
flutter run
```

---

## Estructura target (feature-first)

```
flutter_app/
├── lib/
│   ├── main.dart
│   ├── app/                       # bootstrap del app
│   │   ├── app.dart               # MaterialApp/CupertinoApp raíz
│   │   ├── router.dart            # go_router o AutoRoute
│   │   ├── theme.dart
│   │   └── di.dart                # inyección de dependencias (get_it/riverpod)
│   │
│   ├── core/                      # transversal, sin UI
│   │   ├── network/               # dio client, interceptors, auth token
│   │   ├── storage/               # secure_storage, shared_prefs
│   │   ├── errors/                # Failure, exceptions
│   │   ├── utils/                 # helpers, extensions
│   │   └── constants.dart
│   │
│   ├── features/                  # una carpeta por dominio, espeja apps/ del backend
│   │   ├── accesos/
│   │   │   ├── data/              # datasources (remote/local), DTOs, repos impl
│   │   │   ├── domain/            # entities, repos abstractos, usecases
│   │   │   └── presentation/      # screens, widgets, blocs/notifiers
│   │   ├── asistencia/            # (equivale a recursoshumanos del backend)
│   │   ├── calidad/
│   │   ├── cotizaciones/
│   │   ├── inventario/
│   │   ├── metricas/
│   │   ├── personal/
│   │   └── proyectos/
│   │
│   └── shared/                    # widgets y modelos reutilizables entre features
│       ├── widgets/
│       └── models/
│
├── assets/
│   ├── images/
│   ├── icons/
│   └── fonts/
│
├── test/
│   ├── features/                  # tests unitarios por feature
│   └── helpers/
│
├── pubspec.yaml
├── .env.example                   # variables públicas (API_BASE_URL, etc.)
└── README.md
```

**Regla:** dentro de cada `features/<x>/`, seguir las 3 capas (`data`, `domain`, `presentation`). Nunca importar entre features — si dos features necesitan lo mismo, va a `shared/` o `core/`.

---

## Convenciones sugeridas

- **Nombres de carpetas y archivos:** `snake_case`.
- **State management:** definir uno solo (`riverpod`, `bloc`, `provider`). Recomendado empezar con `riverpod` por simplicidad y testabilidad.
- **Networking:** `dio` con interceptor de auth (token JWT en `secure_storage`).
- **Routing:** `go_router`.
- **Codegen:** `build_runner` + `freezed` + `json_serializable` (los `*.g.dart` y `*.freezed.dart` ya están en `.gitignore`).
- **API base URL:** en `.env` (usar `flutter_dotenv`), NUNCA hardcodear.

---

## Comunicación con el backend

- La API vive en `admin_panel/api_urls.py` y en `apps/api/` del monorepo.
- Autenticación: `rest_framework.authtoken` está registrado en `INSTALLED_APPS`.
- En desarrollo local, el emulador de Android accede al host mediante `10.0.2.2:8000`; iOS simulator usa `localhost:8000`.

---

## No versionar

Ya cubierto por `flutter_app/.gitignore`:
- `.dart_tool/`, `build/`, `.pub-cache/`
- Codegen: `*.g.dart`, `*.freezed.dart`, `*.mocks.dart`
- Keystores Android (`*.jks`, `key.properties`)
- `ios/Pods/`, `ios/Flutter/Generated.xcconfig`
- `.env` (variables reales)
