# Sistema de paquetería

Proyecto final de Programación Orientada a Objetos. **Tema 3: Servicio de paquetería.** Brigada 8.

Sistema de terminal que cotiza y registra envíos (sobres, paquetes, paquetes frágiles y refrigerados), los rastrea, cambia su estado respetando las reglas, los asigna a repartidores sin exceder la capacidad de su vehículo, importa envíos desde CSV, genera el reporte diario, conserva todo entre ejecuciones y simula una jornada de reparto con un hilo por repartidor.

## Integrantes

- Mora Chávez Héctor Cristóbal
- Rodríguez González Adrián
- Cerritos Serrano Angélica
- Angel Emanuel Jose Juarez

## Requisitos

- **Python 3.10 o más reciente.**
- Solo usa la biblioteca estándar, así que no hay que instalar paquetes (por eso no hay `requirements.txt`).

## Instalación

```bash
git clone https://github.com/Lodrey3/Proyecto-POO-Brigada-8.git
cd Proyecto-POO-Brigada-8
python --version        # debe ser 3.10 o más
```

En Linux o macOS puede que el comando sea `python3` en lugar de `python`.

## Cómo ejecutar

Todos los comandos se ejecutan **desde la carpeta raíz del repositorio**.

```bash
python -m paqueteria            # abre el menú interactivo
python -m paqueteria --help     # lista de comandos
python -m paqueteria COMANDO --help
```

Opciones globales (van **antes** del comando):

| Opción | Para qué sirve |
|---|---|
| `--fecha-hora "AAAA-MM-DD HH:MM"` | Fija la fecha y hora de las operaciones. Así se prueban las reglas de fecha sin esperar. |
| `--datos CARPETA` | Carpeta con `tarifas.csv`, `zonas.csv` y `repartidores.json` (por omisión, `datos`). |
| `--ejecucion CARPETA` | Carpeta donde el programa guarda sus datos (por omisión, `ejecucion`, ignorada por git). |

Para empezar de cero, borra la carpeta `ejecucion/`.

## Cómo probar cada función

Esta secuencia usa los datos de ejemplo. Conviene correrla en orden, empezando sin la carpeta `ejecucion/`. Las guías tienen el formato `PQ-AAAAMMDD-NNNN`; si las guías que te salen son distintas, usa las tuyas.

### 1. Cotizar y registrar con guía única

```bash
# Cotiza un paquete frágil express a Guadalajara (zona nacional). Total esperado: $591.60
python -m paqueteria --fecha-hora "2026-11-20 09:00" cotizar --tipo fragil --servicio express --destinatario-cp 44100 --peso 2 --largo 40 --ancho 30 --alto 20 --valor 1000

# Registra un paquete. Responde con la guía PQ-20261120-0001
python -m paqueteria --fecha-hora "2026-11-20 09:05" registrar --tipo paquete --servicio estandar --remitente-nombre "Héctor Mora" --remitente-telefono 5512345678 --remitente-cp 04510 --destinatario-nombre "Ana Ruiz" --destinatario-telefono 5587654321 --destinatario-cp 03100 --peso 3 --largo 30 --ancho 20 --alto 15 --valor 500
```

Casos que se rechazan:

```bash
# Refrigerado a zona nacional
python -m paqueteria cotizar --tipo refrigerado --servicio express --destinatario-cp 44100 --peso 2 --largo 40 --ancho 30 --alto 20 --valor 1000
# Refrigerado por servicio estándar
python -m paqueteria cotizar --tipo refrigerado --servicio estandar --destinatario-cp 03100 --peso 2 --largo 40 --ancho 30 --alto 20 --valor 1000
# Código postal sin zona y peso negativo
python -m paqueteria cotizar --tipo paquete --servicio estandar --destinatario-cp 00123 --peso 2 --largo 10 --ancho 10 --alto 10 --valor 100
python -m paqueteria cotizar --tipo paquete --servicio estandar --destinatario-cp 03100 --peso -2 --largo 10 --ancho 10 --alto 10 --valor 100
```

### 2. Importar envíos desde CSV

```bash
# 12 envíos válidos de un cliente empresarial
python -m paqueteria --fecha-hora "2026-11-20 09:10" importar datos/envios_cliente.csv
# Archivo con errores: importa 2 e informa 10 renglones rechazados con su motivo
python -m paqueteria --fecha-hora "2026-11-20 09:15" importar datos/envios_con_errores.csv
# Archivo dañado (columnas equivocadas) y archivo que no existe
python -m paqueteria importar datos/envios_danado.csv
python -m paqueteria importar datos/no_existe.csv
```

### 3. Cambiar el estado (y cancelar)

```bash
# Cancela un envío que todavía no sale a ruta
python -m paqueteria --fecha-hora "2026-11-20 09:20" cancelar PQ-20261120-0012
# Rechazo: no se puede entregar algo que no está en ruta
python -m paqueteria --fecha-hora "2026-11-20 09:21" estado PQ-20261120-0002 entregar
# Recibe en el almacén todos los envíos registrados (* = todas las guías que lo permitan)
python -m paqueteria --fecha-hora "2026-11-20 10:00" estado "*" ingresar_a_almacen
# Tres intentos fallidos: al tercero se devuelve al remitente
python -m paqueteria --fecha-hora "2026-11-20 10:30" estado PQ-20261120-0013 salir_a_ruta
python -m paqueteria --fecha-hora "2026-11-20 10:40" estado PQ-20261120-0013 registrar_intento_fallido
python -m paqueteria --fecha-hora "2026-11-20 10:50" estado PQ-20261120-0013 salir_a_ruta
python -m paqueteria --fecha-hora "2026-11-20 11:00" estado PQ-20261120-0013 registrar_intento_fallido
python -m paqueteria --fecha-hora "2026-11-20 11:10" estado PQ-20261120-0013 salir_a_ruta
python -m paqueteria --fecha-hora "2026-11-20 11:20" estado PQ-20261120-0013 registrar_intento_fallido
# Rechazo: un envío devuelto ya no se puede cancelar
python -m paqueteria --fecha-hora "2026-11-20 11:30" cancelar PQ-20261120-0013
# Rechazo: una fecha anterior al último movimiento
python -m paqueteria --fecha-hora "2026-11-19 08:00" estado PQ-20261120-0002 salir_a_ruta
```

Acciones válidas: `ingresar_a_almacen`, `salir_a_ruta`, `entregar`, `registrar_intento_fallido`, `cancelar`.

### 4. Rastrear una guía

```bash
python -m paqueteria rastrear PQ-20261120-0013     # estado Devuelto y su historial con fecha y hora
python -m paqueteria rastrear PQ-99999999-0000     # rechazo: la guía no existe
python -m paqueteria listar --estado EnAlmacen     # lista los envíos en un estado
```

### 5. Asignar envíos a repartidores

```bash
python -m paqueteria repartidores                                  # 2 motocicletas (20 kg) y 2 camionetas (500 kg)
python -m paqueteria --fecha-hora "2026-11-20 11:40" asignar       # nunca excede la capacidad
python -m paqueteria repartidores                                  # carga de cada uno
python -m paqueteria --fecha-hora "2026-11-20 11:45" asignar       # ya no hay pendientes
```

El paquete de 120 kg solo puede ir en camioneta. Si se cancela un envío asignado, se quita de su repartidor.

### 6. Simular la jornada de reparto

```bash
python -m paqueteria --fecha-hora "2026-11-20 12:00" simular
```

Con `simular --semilla 7` (en lugar del comando anterior) la simulación sale igual cada vez. Una segunda simulación seguida avisa que ya nadie tiene envíos asignados: primero hay que volver a pasar envíos al almacén y asignarlos.

Todos los repartidores trabajan al mismo tiempo (un hilo cada uno). La central muestra el avance mientras ocurre, el 10 % de los intentos fallan y al final el sistema verifica que el estado de cada envío corresponda a lo que pasó. La bitácora queda en `ejecucion/bitacoras/`. Si nadie tiene envíos asignados, el programa lo avisa.

### 7. Reporte de un día

```bash
python -m paqueteria --fecha-hora "2026-11-20 19:00" reporte
python -m paqueteria reporte --fecha 2026-11-20
```

Muestra y guarda en `ejecucion/reportes/` los envíos por estado, los ingresos por tipo de envío y por servicio y las entregas por repartidor.

### 8. Conservar los datos entre ejecuciones

Cada comando anterior es una ejecución distinta del programa y todos ven los cambios de los anteriores: los envíos, su historial, los repartidores y el contador de guías se guardan en `ejecucion/` (archivos JSON con escritura atómica).

### Archivos faltantes o dañados

```bash
# Tarifas con un dato que no es número
python -m paqueteria --datos datos/con_errores listar
# Carpeta de datos que no existe
python -m paqueteria --datos no_existe listar
# Fecha mal escrita
python -m paqueteria --fecha-hora "20/11/2026" listar
```

Para probar un archivo de ejecución dañado, escribe cualquier texto dentro de `ejecucion/envios.json` y corre `python -m paqueteria listar`: el programa avisa y termina de forma ordenada sin sobrescribir el archivo.

En todos los casos el programa muestra un mensaje claro, nunca un traceback.

### Menú interactivo

`python -m paqueteria --fecha-hora "2026-11-20 09:00"` abre el menú con todas las funciones. La opción `f` cambia la fecha y hora sin salir del programa.

### Pruebas unitarias

```bash
python -m unittest
```

Son 29 pruebas: tarifas y orden del cálculo, reglas de validación, transiciones de estado, capacidad de los vehículos, importación, persistencia, guías únicas con varios hilos, consistencia de la jornada y reporte.

## Estructura del proyecto

```
├── README.md
├── .gitignore
├── docs/
│   ├── diseno.md          documento de diseño
│   └── uml/               diagramas UML (PNG y fuentes .dot)
├── datos/                 datos de ejemplo, incluidos archivos con errores
├── tests/                 pruebas con unittest
└── paqueteria/
    ├── __main__.py        permite ejecutar con python -m paqueteria
    ├── cli/               terminal: argparse (main.py) y menú (menu.py)
    ├── modelo/            envíos, estados, servicios, contactos, tarifas, vehículos y repartidores
    ├── servicios/         fachada SistemaPaqueteria, fábrica, guías, registro, asignación, importación y reportes
    ├── concurrencia/      simulación: hilos de repartidores, central de monitoreo y observadores
    ├── persistencia/      repositorio JSON y serializador de envíos
    ├── util/              relojes (real y simulado)
    └── excepciones/       jerarquía de excepciones propias
```

### Datos de ejemplo (`datos/`)

| Archivo | Contenido |
|---|---|
| `tarifas.csv` | Tarifa del sobre y por kilo de cada zona |
| `zonas.csv` | Zona según los dos primeros dígitos del código postal |
| `repartidores.json` | Repartidores iniciales (se cargan en la primera ejecución) |
| `envios_cliente.csv` | 12 envíos válidos de un cliente empresarial |
| `envios_con_errores.csv` | 2 envíos válidos y 10 con errores distintos |
| `envios_danado.csv` | CSV con columnas equivocadas |
| `con_errores/` | Configuración con un archivo de tarifas dañado |

El diseño, los diagramas UML y las decisiones están en [`docs/diseno.md`](docs/diseno.md).
