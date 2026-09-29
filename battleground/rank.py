"""战场军衔与晋升系统"""
from dataclasses import dataclass, field

RANK_ORDER = ["recruit", "soldier", "captain", "marshal"]

# 各军衔每周奖励：金币阶梯 + 高级军衔专属特权/外观
WEEKLY_SALARY = {
    "recruit": {"gold": 100, "perks": [], "cosmetics": []},
    "soldier": {"gold": 300, "perks": ["extra_loadout"], "cosmetics": ["soldier_insignia"]},
    "captain": {"gold": 800, "perks": ["extra_loadout", "priority_queue"], "cosmetics": ["captain_insignia", "captain_banner"]},
    "marshal": {"gold": 2000, "perks": ["extra_loadout", "priority_queue", "exclusive_queue"], "cosmetics": ["marshal_insignia", "marshal_banner", "marshal_aura"]},
}

# 表现权重：击杀 / 占点 / 治疗
KILL_POINTS = 2
CAPTURE_POINTS = 5
HEAL_POINTS = 1
WIN_BONUS = 10
LOSS_BASE = 2

DAILY_POINT_LIMIT = 200          # 每日积分上限，防止一天从列兵冲到元帅
PLACEMENT_MATCHES = 10           # 新赛季定级赛场次
PROMOTION_SERIES_WINS = 3        # 晋级赛所需胜场
SEASON_INHERITANCE_RATIO = 0.25  # 上赛季最高军衔积分继承比例
MENTOR_BONUS_RATIO = 0.1         # 带新人（低两段以上队友）的积分加成


@dataclass
class Player:
    pid: str
    name: str
    rank_points: int = 0
    rank: str = "recruit"
    daily_gain: int = 0
    active_days: int = 0
    season_high_rank: str = "recruit"
    promotion_wins: int = 0        # 晋级赛已胜场数
    placement_matches: int = 0     # 定级赛已打场数


class RankSystem:
    def __init__(self):
        self.players: dict[str, Player] = {}
        self.rank_tiers: dict = {"recruit": 0, "soldier": 100, "captain": 500, "marshal": 2000}
        self.season: int = 1
        # 组队贡献表：pid -> 贡献值，由战斗统计写入
        self.player_contribution: dict[str, float] = {}

    # ---- bug1: 积分 = 胜负基础分 + 个人表现分 ----
    def calculate_points(self, win: bool, kills: int, captures: int, heals: int) -> int:
        performance = kills * KILL_POINTS + captures * CAPTURE_POINTS + heals * HEAL_POINTS
        base = WIN_BONUS if win else LOSS_BASE
        return base + performance

    # ---- bug2: 每日积分上限 ----
    def get_daily_limit(self) -> int:
        return DAILY_POINT_LIMIT

    def apply_daily_gain(self, player: Player, points: int) -> int:
        """计入每日上限，返回实际入账积分。"""
        room = max(0, self.get_daily_limit() - player.daily_gain)
        gained = min(points, room)
        player.daily_gain += gained
        player.rank_points += gained
        return gained

    # ---- bug3: 衰减按活跃天数，长期不打缓慢下降 ----
    def get_decay_rate(self, active_days: int) -> float:
        if active_days >= 20:
            return 0.0
        # 活跃越少衰减越高，完全不活跃每周衰减 5%
        return 0.05 * (1 - active_days / 20)

    def apply_decay(self, player: Player) -> int:
        rate = self.get_decay_rate(player.active_days)
        decayed = int(player.rank_points * rate)
        player.rank_points = max(0, player.rank_points - decayed)
        return decayed

    # ---- bug4: 匹配按军衔分段，相邻段可排，跨段不可 ----
    def can_match(self, p1_rank: str, p2_rank: str) -> bool:
        i1 = RANK_ORDER.index(p1_rank)
        i2 = RANK_ORDER.index(p2_rank)
        return abs(i1 - i2) <= 1

    def cross_tier_compensation(self, player_rank: str, opponent_rank: str) -> int:
        """跨段对局的积分补偿：挑战高段获胜额外加分，输给低段少扣分。"""
        diff = RANK_ORDER.index(opponent_rank) - RANK_ORDER.index(player_rank)
        return max(0, diff) * 5

    # ---- bug5: 周薪按军衔阶梯 + 专属特权/外观 ----
    def get_weekly_salary(self, rank: str) -> dict:
        return dict(WEEKLY_SALARY.get(rank, WEEKLY_SALARY["recruit"]))

    # ---- bug6: 组队积分按个人贡献分配，带新人有加成 ----
    def distribute_team_points(self, team: list[str], total: int) -> dict:
        contributions = {pid: max(0.0, float(self.player_contribution.get(pid, 0))) for pid in team}
        contrib_sum = sum(contributions.values())
        if contrib_sum <= 0:
            # 无贡献数据时退化为平均分配
            share = total // len(team)
            return {pid: share for pid in team}
        result = {}
        for pid in team:
            share = total * contributions[pid] / contrib_sum
            if self._has_newbie_teammate(pid, team):
                share *= 1 + MENTOR_BONUS_RATIO
            result[pid] = int(round(share))
        return result

    def _has_newbie_teammate(self, pid: str, team: list[str]) -> bool:
        me = self.players.get(pid)
        if me is None:
            return False
        my_tier = RANK_ORDER.index(me.rank)
        for other in team:
            if other == pid:
                continue
            mate = self.players.get(other)
            if mate is not None and my_tier - RANK_ORDER.index(mate.rank) >= 2:
                return True
        return False

    # ---- 晋升：不能跳级，需打晋级赛 ----
    def check_promotion(self, player: Player) -> str:
        """积分达到下一段门槛时进入晋级赛，晋级赛胜场达标才升一级。"""
        idx = RANK_ORDER.index(player.rank)
        if idx >= len(RANK_ORDER) - 1:
            return player.rank
        next_rank = RANK_ORDER[idx + 1]
        if player.rank_points >= self.rank_tiers[next_rank] and player.promotion_wins >= PROMOTION_SERIES_WINS:
            player.rank = next_rank
            player.promotion_wins = 0
            if RANK_ORDER.index(player.season_high_rank) < idx + 1:
                player.season_high_rank = next_rank
        return player.rank

    # ---- bug7: 赛季重置，定级赛 + 上赛季最高军衔部分继承 ----
    def get_season_inheritance(self, last_rank: str) -> int:
        return int(self.rank_tiers.get(last_rank, 0) * SEASON_INHERITANCE_RATIO)

    def start_new_season(self) -> None:
        self.season += 1
        for player in self.players.values():
            inherited = self.get_season_inheritance(player.season_high_rank)
            player.rank_points = inherited
            player.rank = "recruit"
            player.daily_gain = 0
            player.promotion_wins = 0
            player.placement_matches = 0
            player.season_high_rank = "recruit"
