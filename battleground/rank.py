"""战场军衔与晋升系统 - 含7个bug"""
from dataclasses import dataclass, field

@dataclass
class Player:
    pid: str
    name: str
    rank_points: int = 0
    rank: str = "recruit"
    daily_gain: int = 0  # bug2: 无每日上限

class RankSystem:
    def __init__(self):
        self.players: dict[str, Player] = {}
        self.rank_tiers: dict = {"recruit": 0, "soldier": 100, "captain": 500, "marshal": 2000}
        self.season: int = 1

    def calculate_points(self, win: bool, kills: int, captures: int, heals: int) -> int:
        # bug1: 只看胜负
        return 10 if win else 0

    def get_daily_limit(self) -> int:
        # bug2: 无每日上限
        return 999999

    def get_decay_rate(self, active_days: int) -> float:
        # bug3: 只看离线
        return 0.0

    def can_match(self, p1_rank: str, p2_rank: str) -> bool:
        # bug4: 可跨段匹配
        return True

    def get_weekly_salary(self, rank: str) -> dict:
        # bug5: 固定薪资
        return {"gold": 100}

    def distribute_team_points(self, team: list[str], total: int) -> dict:
        # bug6: 平均分
        return {pid: total // len(team) for pid in team}

    def get_season_inheritance(self, last_rank: str) -> int:
        # bug7: 无赛季重置
        return self.rank_tiers.get(last_rank, 0)
