# Motor de reglas de validación de marcación (CAV-12 / HT-02)

Documento de referencia para QA. Describe cómo el sistema clasifica la marcación
de asistencia de un trabajador en un día dado.

- **Código:** [`apps/recursoshumanos/motor_reglas.py`](../apps/recursoshumanos/motor_reglas.py)
- **Punto de integración:** `recalcular_asistencia_diaria` en
  [`apps/recursoshumanos/services.py`](../apps/recursoshumanos/services.py)
- **Pruebas:** [`apps/recursoshumanos/tests/`](../apps/recursoshumanos/tests)

## Qué hace el motor

Recibe un `ContextoMarcacion` (datos ya resueltos, en hora local) y devuelve un
`ResultadoEvaluacion`. Evalúa **feriado + horario + tolerancia en una sola
pasada**: quien lo invoca recolecta los datos de BD una vez y el motor decide en
memoria, sin volver a consultar. Por eso es una función pura y se prueba sin BD.

### Entradas (`ContextoMarcacion`)

| Campo | Significado |
|---|---|
| `fecha` | Día evaluado. |
| `estado_jornada` | Tipo de jornada del `TareoDiario.estado`: `C` Campo, `O` Oficina, `P` Personalizado, `J` Jornada por horas, `D` Día libre. |
| `resultado_previo` | Resultado que ya tenía el día: `F` Falta, `A` Asistió, `J` Justificado. |
| `hora_entrada_programada` / `hora_salida_programada` | Horario planificado del día. |
| `hora_entrada_real` / `hora_salida_real` | Primera marca de Entrada y última de Salida reales. |
| `minutos_tolerancia` | Minutos de gracia configurados por **Sede × tipo de horario** (`ConfiguracionTolerancia`, CAV-15). |
| `es_feriado` | Si la fecha es feriado **para ese trabajador**, resuelto por scope (ver abajo). |
| `nombre_feriado` / `ambito_feriado` | Nombre y ámbito del feriado aplicable, solo para el detalle legible. |
| `tiene_marcas` | Si hubo alguna marcación real ese día. |

**Scope del feriado (CAV-13).** El servicio `obtener_feriado(fecha, sede, empresa)`
decide si un feriado aplica al trabajador según el ámbito (`Feriado.aplica_a`):
`NACIONAL` (sin sede/empresa) aplica a todos; `REGIONAL`/`LOCAL` solo a su sede;
`EMPRESA` solo a su empresa. Como `Feriado.fecha` es única, hay a lo sumo un
feriado por día. El `detalle_marca` incluye el nombre y ámbito (ej.
*"Asistencia en día feriado: Inti Raymi (Regional)"*).

### Salidas (`ResultadoEvaluacion`)

| Campo | Significado |
|---|---|
| `resultado` | `F` / `A` / `J`. Se persiste en `TareoDiario.resultado`. |
| `etiqueta` | Etiqueta principal (`EstadoMarca`). Se persiste en `TareoDiario.etiqueta_estado`. |
| `etiquetas` | Todas las etiquetas aplicables (p. ej. TARDANZA + FUERA_DE_HORARIO). |
| `horas_tardanza` / `minutos_tardanza` | Tardanza tras aplicar la tolerancia. |
| `detalle` | Motivo legible de la clasificación (p. ej. "Tardanza de 15 min (tolerancia: 15 min); Salida posterior"). Se persiste en `TareoDiario.detalle_marca`. |

## Etiquetas de estado (`EstadoMarca`)

| Etiqueta | Cuándo se asigna |
|---|---|
| `NORMAL` | Día normal con marcas, dentro de horario y de tolerancia. |
| `TARDANZA` | Entrada real posterior a `entrada_programada + tolerancia`. |
| `FERIADO` | El día es feriado (con o sin marcas). |
| `FUERA_DE_HORARIO` | La entrada real cae antes de `entrada_programada - tolerancia`, la salida real después de `salida_programada + tolerancia`, o la salida real antes de `salida_programada - tolerancia`. |
| `FALTA` | Día normal sin ninguna marca. |
| `JUSTIFICADO` | El día ya estaba justificado (aprobado por RRHH o vía ERP). |
| `DIA_LIBRE` | El día estaba programado como libre (`estado = 'D'`). |
| `SIN_HORARIO` | Hay marcas pero el día no tiene horario de entrada programado. |

## Orden de prioridad de las reglas

El motor evalúa en este orden y devuelve en cuanto una regla aplica:

1. **Justificado manda.** Si `resultado_previo == 'J'` → `JUSTIFICADO`. La
   justificación la aprueba RRHH o llega del ERP; una marca suelta no la pisa.
2. **Día libre.** Si `estado_jornada == 'D'` → `DIA_LIBRE` (no se evalúa
   tardanza aunque existan marcas sueltas).
3. **Sin marcas.** Si es feriado → `FERIADO` (no penaliza, el resultado no se
   fuerza a Falta); si no → `FALTA` (`resultado = 'F'`).
4. **Feriado con marcas.** → `Asistió` + `FERIADO`. Trabajar en feriado **no**
   genera tardanza.
5. **Día normal con marcas.** → `Asistió`, y según el horario:
   - sin horario de entrada programado → `SIN_HORARIO`;
   - `entrada_real > entrada_programada + tolerancia` → `TARDANZA`;
   - marca fuera del rango programado → `FUERA_DE_HORARIO`;
   - en caso contrario → `NORMAL`.

## Casos límite a cubrir en pruebas

- **Tolerancia en el minuto exacto:** si `entrada_real == entrada_programada +
  tolerancia`, **NO** es tardanza (el umbral es estricto, `> 0`).
- **Feriado fuera de horario:** en feriado la etiqueta es `FERIADO` y **no** se
  calcula tardanza aunque la entrada sea tardía.
- **Día libre con marca:** queda `DIA_LIBRE`, resultado `Asistió`, sin tardanza.
- **Sin horario programado pero con marca:** `SIN_HORARIO` (no se inventa
  tardanza sin referencia de entrada).
- **Justificado que igual marcó:** permanece `JUSTIFICADO` (no pasa a Asistió).
- **Prioridad de tolerancia por Sede vs. horario:** dos `ConfiguracionTolerancia`
  distintas para la misma Sede pero diferente `tipo_horario`, o para distinta
  Sede, deben producir tardanzas distintas para la misma marca.

## Alcance y deuda técnica

El motor está integrado en `recalcular_asistencia_diaria`, que es el punto por el
que pasan el registro de la app móvil (`apps/api/views.py`) y el `post_save` de
`Asistencia` (`apps/recursoshumanos/signals.py`).

**Aún NO pasan por el motor** (clasifican con lógica propia y duplicada; deuda
técnica pendiente de unificar en una HU futura):

- Import biométrico — `apps/recursoshumanos/servicios_asistencias.py` (usa horario
  de referencia hardcodeado y no consulta la tolerancia configurable ni feriados).
- Import de Excel de métricas — `apps/metricas_ceneris/views.py`.
- Reportes — `apps/recursoshumanos/views.py` (etiquetas calculadas inline) y el
  calendario de feriados hardcodeado con `easter()` en métricas, paralelo a la
  tabla oficial `Feriado`.
