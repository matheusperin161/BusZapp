"""
simulate_bus.py — Simula ônibus percorrendo rotas em Chapecó
------------------------------------------------------------
Uso:
    python simulate_bus.py                      # simula 1 ônibus na linha 1
    python simulate_bus.py --line 2             # linha 2
    python simulate_bus.py --line 1 --bus-id 101  # ônibus específico
    python simulate_bus.py --all                # simula todos as linhas ao mesmo tempo
    python simulate_bus.py --speed 3            # 3x mais rápido
"""
import time, argparse, requests, threading

BASE_URL = "http://localhost:8080"

# Paradas por linha (mesmas do seed.py)
LINES = {
    '1': [(-27.10597,-52.61336),(-27.10280,-52.61490),(-27.09980,-52.61620),
          (-27.09650,-52.61710),(-27.09310,-52.61800),(-27.08980,-52.61820),
          (-27.08620,-52.61830),(-27.08012,-52.61850)],
    '2': [(-27.10597,-52.61336),(-27.10600,-52.62100),(-27.10610,-52.62800),
          (-27.10600,-52.63200),(-27.10650,-52.63700),(-27.10750,-52.64100),
          (-27.10890,-52.64500)],
    '3': [(-27.10597,-52.61336),(-27.10400,-52.61500),(-27.10200,-52.61650),
          (-27.10350,-52.61900),(-27.10550,-52.62050),(-27.10600,-52.61700),
          (-27.10597,-52.61336)],
    '4': [(-27.10597,-52.61336),(-27.10800,-52.61900),(-27.11000,-52.62500),
          (-27.11200,-52.63200),(-27.11350,-52.63900),(-27.11420,-52.64500),
          (-27.11500,-52.65200)],
    '5': [(-27.10597,-52.61336),(-27.10750,-52.61500),(-27.10950,-52.61600),
          (-27.11200,-52.61900),(-27.11500,-52.62100),(-27.11800,-52.62500)],
}
STEPS = 20

def lerp(a, b, t): return a + (b - a) * t

def send(bus_id, lat, lng, bus_number):
    try:
        r = requests.post(f"{BASE_URL}/api/update_location",
            json={"bus_id": bus_id, "latitude": lat, "longitude": lng, "bus_number": bus_number},
            timeout=4)
        return r.status_code == 200
    except:
        return False

def run_bus(line, bus_id, bus_number, interval, loop=True):
    stops = LINES.get(str(line), LINES['1'])
    print(f"🚌 Linha {line} | Ônibus {bus_number} (ID={bus_id}) iniciado")
    iteration = 0
    while True:
        iteration += 1
        for i in range(len(stops) - 1):
            o, d = stops[i], stops[i+1]
            for step in range(STEPS + 1):
                t = step / STEPS
                send(bus_id, lerp(o[0],d[0],t), lerp(o[1],d[1],t), bus_number)
                time.sleep(interval)
        print(f"  ✓ Linha {line} / Ônibus {bus_number} — volta {iteration} completa")
        if not loop: break

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--line',   default='1',   help='Número da linha (1-5)')
    parser.add_argument('--bus-id', type=int,      help='ID do ônibus (padrão: auto)')
    parser.add_argument('--speed',  type=float, default=1.0, help='Multiplicador de velocidade')
    parser.add_argument('--all',    action='store_true',     help='Simular todas as linhas')
    parser.add_argument('--no-loop',action='store_true',     help='Rodar uma vez só')
    args = parser.parse_args()

    interval = max(0.05, 0.4 / args.speed)

    if args.all:
        threads = []
        for line in LINES:
            bus_id = int(line) * 100 + 1
            t = threading.Thread(target=run_bus, args=(line, bus_id, f"{line}01", interval, not args.no_loop), daemon=True)
            threads.append(t)
            t.start()
            time.sleep(0.5)  # stagger start
        print(f"\n✅ {len(threads)} ônibus simulados. Pressione Ctrl+C para parar.\n")
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            print("\nSimulação encerrada.")
    else:
        bus_id = args.bus_id or (int(args.line) * 100 + 1)
        bus_number = f"{args.line}01"
        run_bus(args.line, bus_id, bus_number, interval, not args.no_loop)
