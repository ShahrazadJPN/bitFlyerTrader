from ConditionChecker import ConditionChecker
import time
import traceback


if __name__ == '__main__':
    c = ConditionChecker()
    try:
        while True:
            c.board_status_checker()      # とりあえず鯖状態を確認
            c.sfd_status_checker()        # sfdを確認
            c.renew_chart_data()          # 最新のewmaほかを手に入れる
            c.order_checker()             # 注文中か否か
            c.position_checker()          # ポジション確認
            c.only_position_checker()     # ポジションしかない場合の動作を行う
            c.order_actually_dead_checker()   # 注文が実質死亡していないか確認する
            c.only_order_checker()        # 注文しかない場合の処理を行う →場合によってはここで注文をキャンセルする
            c.slippage_checker()

    except:
        time.sleep(2)
        traceback.print_exc()