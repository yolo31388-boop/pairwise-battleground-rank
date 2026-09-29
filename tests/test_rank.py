"""战场军衔与晋升系统 - 红态测试"""
import pytest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from battleground.rank import RankSystem, Player

class TestPointCalculation:
    def test_performance_affects_points(self):
        rs = RankSystem()
        p1 = rs.calculate_points(win=True, kills=0, captures=0, heals=0)
        p2 = rs.calculate_points(win=True, kills=20, captures=5, heals=10)
        assert p2 > p1  # bug1: 都是10

class TestDailyLimit:
    def test_daily_points_capped(self):
        rs = RankSystem()
        limit = rs.get_daily_limit()
        assert limit < 10000  # bug2: 999999

class TestDecay:
    def test_inactive_players_decay(self):
        rs = RankSystem()
        d_active = rs.get_decay_rate(active_days=30)
        d_inactive = rs.get_decay_rate(active_days=0)
        assert d_inactive > d_active  # bug3: 都是0

class TestMatchmaking:
    def test_low_rank_cannot_match_high_rank(self):
        rs = RankSystem()
        assert rs.can_match("recruit", "marshal") == False  # bug4: True
        assert rs.can_match("recruit", "soldier") == True

class TestSalaryByRank:
    def test_higher_rank_better_salary(self):
        rs = RankSystem()
        s1 = rs.get_weekly_salary("recruit")
        s2 = rs.get_weekly_salary("marshal")
        assert s2["gold"] > s1["gold"]  # bug5: 都是100

class TestTeamPointDistribution:
    def test_carry_gets_more_points(self):
        rs = RankSystem()
        # 应该按贡献分配，不是平均
        assert hasattr(rs, "player_contribution")
        team = ["p1", "p2"]
        rs.player_contribution = {"p1": 100, "p2": 10}
        result = rs.distribute_team_points(team, 110)
        assert result["p1"] > result["p2"]  # bug6: 平均分

class TestSeasonReset:
    def test_new_season_starts_from_placement(self):
        rs = RankSystem()
        inheritance = rs.get_season_inheritance("marshal")
        assert inheritance < rs.rank_tiers["marshal"]  # bug7: 完全继承=2000
        assert inheritance > 0  # 但有部分继承
