#!/usr/bin/env python3
"""PYRE ALLEY — neon skee-ball arcade for ElbowOS. Python 3 + pygame."""
import math, os, random, subprocess, sys

RECORD = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
PLAY = "--play" in sys.argv
if RECORD or not PLAY:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

W, H, FPS, SECS = 1080, 1920, 30, 15
OUT = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/PYRE_ALLEY_ElbowOS.mp4")
TITLE, HANDLE = "PYRE ALLEY", "x.com/ElbowOS"

PLUM = (18, 6, 22)
INK = (38, 10, 28)
RAMP = (62, 18, 28)
CORAL = (255, 92, 64)
MAG = (255, 48, 140)
GOLD = (255, 196, 48)
LIME = (170, 255, 70)
CYAN = (70, 230, 255)
WHITE = (255, 244, 230)
AMBER = (255, 150, 36)
VIO = (180, 70, 255)

CUPS = [
    {"x": 540, "y": 430, "r": 52, "pts": 100, "col": GOLD},
    {"x": 300, "y": 560, "r": 64, "pts": 50, "col": MAG},
    {"x": 780, "y": 560, "r": 64, "pts": 50, "col": MAG},
    {"x": 200, "y": 740, "r": 72, "pts": 30, "col": CYAN},
    {"x": 540, "y": 720, "r": 78, "pts": 20, "col": LIME},
    {"x": 880, "y": 740, "r": 72, "pts": 30, "col": CYAN},
]


class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        flags = 0 if PLAY else pygame.HIDDEN
        try:
            self.screen = pygame.display.set_mode((W, H), flags)
        except pygame.error:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            pygame.display.quit()
            pygame.display.init()
            self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption(TITLE)
        self.font_lg = pygame.font.SysFont("DejaVu Sans", 58, bold=True)
        self.font = pygame.font.SysFont("DejaVu Sans", 38, bold=True)
        self.font_sm = pygame.font.SysFont("DejaVu Sans", 26)
        self.clock = pygame.time.Clock()
        self.score = self.best = self.t = 0
        self.combo = self.banner = self.flash = 0
        self.banner_txt = ""
        self.power = 0.45
        self.charging = False
        self.aim = 0.0
        self.balls, self.sparks, self.pops, self.embers = [], [], [], []
        for _ in range(55):
            self.embers.append([random.randint(80, W - 80), random.randint(200, H - 200),
                                random.uniform(-0.4, 0.4), random.uniform(-1.8, -0.4),
                                random.choice([CORAL, AMBER, MAG, GOLD])])
        self.next_shot = 8
        self.shots_left = 12

    def launch(self, power=None, aim=None):
        if self.shots_left <= 0:
            self.shots_left = 12
        p = 11 + (power if power is not None else self.power) * 22
        a = -math.pi / 2 + (aim if aim is not None else self.aim)
        self.balls.append({
            "x": W / 2 + random.uniform(-8, 8), "y": 1680.0,
            "vx": math.cos(a) * p * 0.55, "vy": math.sin(a) * p,
            "r": 22, "alive": True, "trail": [],
        })
        self.shots_left -= 1
        self.charging = False
        self.power = 0.35

    def burst(self, x, y, col, n=14):
        for _ in range(n):
            a = random.uniform(0, 6.2832)
            sp = random.uniform(2, 12)
            self.sparks.append([x, y, math.cos(a) * sp, math.sin(a) * sp, 18, col])

    def autoplay(self):
        if self.next_shot > 0:
            return
        cup = random.choice(CUPS)
        dx = cup["x"] - W / 2
        aim = max(-0.42, min(0.42, dx / 900 + random.uniform(-0.08, 0.08)))
        need = 0.38 + (780 - cup["y"]) / 900 + random.uniform(-0.06, 0.1)
        self.launch(power=max(0.28, min(0.98, need)), aim=aim)
        self.next_shot = random.randint(22, 36)

    def tick(self):
        self.t += 1
        self.flash = max(0, self.flash - 1)
        self.banner = max(0, self.banner - 1)
        self.next_shot = max(0, self.next_shot - 1)
        if self.charging:
            self.power = min(1.0, self.power + 0.035)
        for e in self.embers:
            e[0] += e[2]
            e[1] += e[3]
            if e[1] < 180:
                e[1] = H - 160
                e[0] = random.randint(80, W - 80)
        for b in self.balls:
            if not b["alive"]:
                continue
            b["trail"].append((b["x"], b["y"]))
            if len(b["trail"]) > 10:
                b["trail"].pop(0)
            b["vy"] += 0.55
            b["x"] += b["vx"]
            b["y"] += b["vy"]
            if b["x"] < 110 or b["x"] > W - 110:
                b["vx"] *= -0.82
                b["x"] = max(110, min(W - 110, b["x"]))
                self.burst(b["x"], b["y"], AMBER, 6)
            if b["y"] < 210:
                b["vy"] = abs(b["vy"]) * 0.6
                b["y"] = 210
            scored = False
            if b["vy"] > 0 and 360 < b["y"] < 820:
                for c in CUPS:
                    if math.hypot(b["x"] - c["x"], b["y"] - c["y"]) < c["r"] - 8:
                        pts = c["pts"]
                        self.combo += 1
                        gained = pts * (1 + self.combo // 3)
                        self.score += gained
                        self.best = max(self.best, self.score)
                        self.banner, self.banner_txt = 16, f"+{gained}"
                        self.flash = 5
                        self.pops.append([c["x"], c["y"] - 40, f"{c['pts']}", 24, c["col"]])
                        self.burst(c["x"], c["y"], c["col"], 22)
                        b["alive"] = False
                        scored = True
                        break
            if not scored and b["y"] > 1760:
                b["alive"] = False
                self.combo = 0
                self.burst(b["x"], b["y"], CORAL, 8)
        self.balls = [b for b in self.balls if b["alive"] or (b["trail"])]
        for b in self.balls:
            if not b["alive"]:
                b["trail"] = b["trail"][1:]
        self.balls = [b for b in self.balls if b["alive"] or b["trail"]]
        for sp in self.sparks:
            sp[0] += sp[2]
            sp[1] += sp[3]
            sp[3] += 0.25
            sp[4] -= 1
        self.sparks = [sp for sp in self.sparks if sp[4] > 0]
        for p in self.pops:
            p[1] -= 1.6
            p[3] -= 1
        self.pops = [p for p in self.pops if p[3] > 0]

    def draw(self, surf):
        surf.fill(PLUM)
        pygame.draw.rect(surf, INK, (70, 178, W - 140, H - 280), border_radius=40)
        for i in range(8):
            y = 240 + i * 160
            shade = 48 + i * 6
            pygame.draw.rect(surf, (shade, 14, 26), (110, y, W - 220, 148), border_radius=8)
        pygame.draw.rect(surf, RAMP, (160, 1480, W - 320, 220), border_radius=24)
        pygame.draw.rect(surf, CORAL, (160, 1480, W - 320, 220), 4, border_radius=24)
        pygame.draw.rect(surf, AMBER, (88, 200, 18, 1480), border_radius=8)
        pygame.draw.rect(surf, AMBER, (W - 106, 200, 18, 1480), border_radius=8)
        for e in self.embers:
            pygame.draw.circle(surf, e[4], (int(e[0]), int(e[1])), 3)
        for c in CUPS:
            pygame.draw.circle(surf, (20, 4, 12), (int(c["x"]), int(c["y"])), c["r"] + 10)
            pygame.draw.circle(surf, c["col"], (int(c["x"]), int(c["y"])), c["r"], 7)
            pygame.draw.circle(surf, WHITE, (int(c["x"]), int(c["y"])), 10)
            lab = self.font_sm.render(str(c["pts"]), True, c["col"])
            surf.blit(lab, lab.get_rect(center=(c["x"], c["y"] - c["r"] - 22)))
        lx, ly = W / 2, 1688
        pygame.draw.circle(surf, CORAL, (int(lx), int(ly)), 48, 5)
        pygame.draw.circle(surf, GOLD, (int(lx), int(ly)), 18)
        pygame.draw.rect(surf, (40, 8, 16), (140, 1768, 800, 28), border_radius=10)
        pw = int(800 * (self.power if self.charging else 0.12 + 0.2 * math.sin(self.t * 0.2)))
        if not PLAY:
            pw = int(800 * (0.35 + 0.25 * abs(math.sin(self.t * 0.11))))
        pygame.draw.rect(surf, LIME if pw < 560 else CORAL, (140, 1768, max(12, pw), 28), border_radius=10)
        for b in self.balls:
            for i, (tx, ty) in enumerate(b["trail"]):
                pygame.draw.circle(surf, GOLD, (int(tx), int(ty)), max(3, 8 - i))
            if b["alive"]:
                pygame.draw.circle(surf, AMBER, (int(b["x"]), int(b["y"])), b["r"])
                pygame.draw.circle(surf, WHITE, (int(b["x"] - 6), int(b["y"] - 6)), 7)
        for sp in self.sparks:
            pygame.draw.circle(surf, sp[5], (int(sp[0]), int(sp[1])), max(2, sp[4] // 4))
        for p in self.pops:
            t = self.font.render(p[2], True, p[4])
            surf.blit(t, t.get_rect(center=(int(p[0]), int(p[1]))))
        if self.flash:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((255, 90, 40, 32))
            surf.blit(ov, (0, 0))
        if self.banner:
            lab = self.font_lg.render(self.banner_txt, True, GOLD)
            surf.blit(lab, lab.get_rect(center=(W // 2, 250)))
        title = self.font_lg.render(TITLE, True, CORAL)
        surf.blit(title, title.get_rect(center=(W // 2, 72)))
        sub = self.font_sm.render(HANDLE, True, GOLD)
        surf.blit(sub, sub.get_rect(center=(W // 2, 128)))
        sc = self.font.render(f"SCORE  {self.score}", True, WHITE)
        cb = self.font_sm.render(f"COMBO  x{self.combo}   BALLS  {self.shots_left}", True, AMBER)
        hint = self.font_sm.render("A/D aim   HOLD SPACE charge   RELEASE launch", True, CYAN)
        surf.blit(sc, sc.get_rect(center=(W // 2, H - 118)))
        surf.blit(cb, cb.get_rect(center=(W // 2, H - 72)))
        surf.blit(hint, hint.get_rect(center=(W // 2, H - 32)))

    def play_interactive(self):
        running = True
        while running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                    running = False
                if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE, pygame.K_w):
                    self.charging = True
                if ev.type == pygame.KEYUP and ev.key in (pygame.K_SPACE, pygame.K_w):
                    if self.charging:
                        self.launch()
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.aim = max(-0.5, self.aim - 0.025)
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.aim = min(0.5, self.aim + 0.025)
            self.tick()
            self.draw(self.screen)
            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()

    def record(self):
        frames = FPS * SECS
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart",
            OUT,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        canvas = pygame.Surface((W, H))
        try:
            for i in range(frames):
                self.autoplay()
                self.tick()
                self.draw(canvas)
                proc.stdin.write(pygame.image.tostring(canvas, "RGB"))
                if i % 30 == 0:
                    print(f"frame {i}/{frames}", flush=True)
        finally:
            proc.stdin.close()
            err = proc.stderr.read().decode("utf-8", "ignore")
            rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed ({rc}):\n{err[-1200:]}")
        print("wrote", OUT)
        pygame.quit()


def main():
    g = Game()
    if PLAY and not RECORD:
        g.play_interactive()
    else:
        g.record()


if __name__ == "__main__":
    main()
