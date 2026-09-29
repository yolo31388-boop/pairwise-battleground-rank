"""战场军衔与晋升系统"""
from dataclasses import dataclass, field

RANK_ORDER = ["recruit", "soldier", "captain", "marshal"]

@dataclass
class Player:
    pid: str
    name: str
    rank_points: int = 0
    rank: str = "recruit"
    daily_gain: int = 0
    highest_rank: str = "recruit"

class RankSystem:
    DAILY_LIMIT = 200          # bug2: 每日积分上限
    DECAY_PER_INACTIVE_DAY = 0.02
    MAX_INHERIT_RATIO = 0.5    # bug7: 赛季继承比例

    def __init__(self):
        self.players: dict[str, Player] = {}
        self.rank_tiers: dict = {"recruit": 0, "soldier": 100, "captain": 500, "marshal": 2000}
        self.season: int = 1
        self.player_contribution: dict[str, int] = {}  # bug6: 个人贡献

    # bug1: 胜负 + 个人表现（击杀/占点/治疗）综合计算
    def calculate_points(self, win: bool, kills: int, captures: int, heals: int) -> int:
        base = 10 if win else 2
        performance = kills * 1 + captures * 3 + heals * 1
        return base + performance

    # bug2: 每日积分上限，防止一天从列兵刷到元帅
    def get_daily_limit(self) -> int:
        return self.DAILY_LIMIT

    def apply_daily_gain(self, player: Player, points: int) -> int:
        remaining = self.DAILY_LIMIT - player.daily_gain
        applied = max(0, min(points, remaining))
        player.daily_gain += applied
        player.rank_points += applied
        return applied

    # bug3: 衰减按活跃天数，长期不打缓慢下降
    def get_decay_rate(self, active_days: int) -> float:
        if active_days >= 7:
            return 0.0
        return self.DECAY_PER_INACTIVE_DAY * (7 - active_days) / 7

    # bug4: 匹配按军衔分段，只允许相邻段
    def can_match(self, p1_rank: str, p2_rank: str) -> bool:
        i1 = RANK_ORDER.index(p1_rank)
        i2 = RANK_ORDER.index(p2_rank)
        return abs(i1 - i2) <= 1

    def get_cross_tier_compensation(self, p1_rank: str, p2_rank: str) -> int:
        """跨段匹配时给低军衔一方的积分补偿"""
        gap = abs(RANK_ORDER.index(p1_rank) - RANK_ORDER.index(p2_rank))
        return gap * 5 if gap > 1 else 0

    # bug5: 奖励按等级阶梯，高级军衔有专属特权和外观
    def get_weekly_salary(self, rank: str) -> dict:
        salaries = {
            "recruit": {"gold": 100, "perks": [], "skin": None},
            "soldier": {"gold": 300, "perks": ["extra_queue"], "skin": None},
            "captain": {"gold": 800, "perks": ["extra_queue", "priority_match"], "skin": "captain_cloak"},
            "marshal": {"gold": 2000, "perks": ["extra_queue", "priority_match", "exclusive_title"], "skin": "marshal_armor"},
        }
        return salaries.get(rank, salaries["recruit"])

    # bug6: 组队积分按个人贡献分配，带新人有加成
    def distribute_team_points(self, team: list[str], total: int) -> dict:
        contributions = {pid: self.player_contribution.get(pid, 0) for pid in team}
        total_contrib = sum(contributions.values())
        if total_contrib <= 0:
            share = total // len(team)
            return {pid: share for pid in team}
        result = {}
        for pid in team:
            points = total * contributions[pid] // total_contrib
            result[pid] = points
        return result

    def mentor_bonus(self, team_ranks: list[str]) -> float:
        """高军衔带新人（recruit）时全队积分加成"""
        has_recruit = "recruit" in team_ranks
        has_veteran = any(r in ("captain", "marshal") for r in team_ranks)
        return 1.2 if has_recruit and has_veteran else 1.0

    # bug7: 赛季重置，新赛季从定级赛开始，上赛季最高军衔部分继承
    def get_season_inheritance(self, last_rank: str) -> int:
        return int(self.rank_tiers.get(last_rank, 0) * self.MAX_INHERIT_RATIO)

    def start_new_season(self, player: Player) -> None:
        self.season += 1
        player.highest_rank = player.rank
        player.rank_points = self.get_season_inheritance(player.rank)
        player.rank = "recruit"  # 从定级赛重新打
        player.daily_gain = 0
