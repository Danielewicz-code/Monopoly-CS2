import os
import view
import random
import gameboard
import player as plr # avoid naming conflict with the player module
import gamesquare
import observer


class Controller(observer.Observer):
    """Control the game flow"""

    def __init__(self, root):

        #for now we have references to the backend and frontend objects
        #tight coupling is not ideal, but we will refactor later
        super().__init__()
        self._view = view.View(root)

        csv_path = os.path.join("resources", "data", "board.csv")
        names = self._view.ask_for_player_names(3)
        players = self._create_players_from_names(names)
        self._gameboard = gameboard.GameBoard(csv_path, players)

        self._add_listeners()

        self.__dice_rolled = False

        self.__roll_count = 0

        observer.Event("update_state", f"{self._gameboard.get_current_player().name}'s turn")
        observer.Event("update_state_box", str(self._gameboard))

        self._set_expected_val()

    #create the new players with custom names
    def _create_players_from_names(self, names):
        players = []
        for name in names:
            player = plr.Player(name, 1500)
            players.append(player)
        return players

    def _add_listeners(self):
        """Add listeners to the view"""
        self.observe("roll", self._roll_action)
        self.observe("end_turn", self._end_player_turn)
        self.observe("purchase", self._buy_square)
        self.observe("mortgage", self._mortgage)
        self.observe("mortgage_specific", self._mortgage_specific)
        self.observe("unmortgage", self._unmortgage)

    def _test_observers(self, data):
        """Test the observer pattern"""
        print("observed event roll")

    def _create_players(self, num_players):
        """Create num_players players and return a list of them"""
        players = []
        for i in range(num_players):
            player = plr.Player(f"Player {i}", 1500)
            players.append(player)
        return players

    def _set_expected_val(self):
        ev = self._gameboard.calculate_expected_value(self._gameboard.get_current_player().position, 0)
        ev = round(ev, 2)
        observer.Event("update_state", f"Expected value: {ev}")

        player = self._gameboard.get_current_player()
        # add the expected value to the player's luck
        player.luck += ev

    def _roll_dice(self):
        """Simulate the rolling of two dice
            :return the sum of two random dice values
        """
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        dice_sum = dice1 + dice2

        self.__dice_rolled = True
        self.__roll_count += 1

        if dice1 == dice2:
            #double rolled
            observer.Event("update_state", f"Doubles rolled: {dice1}+{dice2} = {dice_sum}")
            self.__dice_rolled = False
        else:
            observer.Event("update_state", f"Dice rolled: {dice1} + {dice2} = {dice_sum}")
        return dice_sum

    def _handle_roll_dice(self):
        """Function to handle the roll dice button click event"""

        if self.__dice_rolled:
            #only one roll per turn
            observer.Event("update_state", "One roll per turn or Doubles required")
            return False

        dice_sum = self._roll_dice()
        player = self._gameboard.get_current_player()

        #move the player
        player.move(dice_sum)
        position = player.position
        square = self._gameboard.get_square(position)

        #if the square is the "Go to jail" one, send the player to jail
        if "GoToJail" in square.space:
            player.go_to_jail()
            observer.Event("update_state", f"{player.name} landed on Go To Jail!")
            observer.Event("update_card", 30)
            self._view.root.after(1500, lambda: observer.Event("update_card", 10))
            return False

        #pay the rent
        #should check if the player has money and if not
        #give them the chance to trade or mortgage
        rent = player.pay_rent(square,dice_sum)
        if rent != 0:
            print(f"rent paid: {rent}")
            player.luck -= rent
            observer.Event("update_state", f"Rent paid: {rent}")

        #no money left?
        if player.money < 0:
            player.declare_bankrupt()

        return True

    def _end_player_turn(self, callback):
        """End the current player's turn"""

        if not self.__dice_rolled:
            #player must roll the dice first
            observer.Event("update_state", "Roll the dice first")
            return
        self.__dice_rolled = False
        self.__roll_count = 0
        player_name = self._gameboard.next_turn()
        observer.Event("update_state_box", str(self._gameboard))
        observer.Event("update_card", self._gameboard.get_current_player().position)
        callback()
        observer.Event("update_state", f"{player_name}'s turn")

        self._set_expected_val()

    def _buy_square(self, data):
        """try to buy the square the active player is currently on"""

        if (self.__roll_count == 0):
            observer.Event("update_state", "Roll the dice first")
            return
        player = self._gameboard.get_current_player()
        position = player.position
        square = self._gameboard.get_square(position)
        buy = player.buy_property(square)
        if buy:
            print(f"Square bought {square}")
            observer.Event("update_state",f"Square bought: {square}" )
        else:
            observer.Event("update_state",f"Square not bought: {square}" )

        observer.Event("update_state_box", str(self._gameboard))

    def _mortgage(self, data):
        """Player has indicated an interest in mortgaging a property
        return their choices as a list of names"""
        player = self._gameboard.get_current_player()
        deeds = player.properties
        # only return the deeds that can be mortgaged
        observer.Event("choice", [d.name for d in deeds if not d.is_mortgaged])
        observer.Event("update_state_box", str(self._gameboard))


    def _mortgage_specific(self, deed_name):
        """Mortgage a specific property"""
        player = self._gameboard.get_current_player()
        res = player.mortgage_property(deed_name)
        print(deed_name)
        if res:
            observer.Event("update_state", f"{deed_name} mortgaged")
        else:
            observer.Event("update_state", f"attempt to mortgage {deed_name} failed")

    def _unmortgage(self, data):
        """Player has indicated an interest in unmortgaging a property
            they must unmortgage in a FIFO order
        """
        player = self._gameboard.get_current_player()
        deed_name = player.unmortgage_property()
        if deed_name != "":
            observer.Event("update_state", f"Unmortgaged: {deed_name}")
            observer.Event("update_state_box", str(self._gameboard))


    def button_clicked(self, button):
        """Handle View button click events"""
        print(f"Button clicked: {button}")
        self._roll_action(None)

    def _roll_action(self, data):
        player = self._gameboard.get_current_player()

    #jail logic to escape, pay, inclrease counter.
        if player.in_jail:
            dice1 = random.randint(1, 6)
            dice2 = random.randint(1, 6)
            observer.Event("update_state", f"{player.name} (in jail) rolled: {dice1} + {dice2}")

            if dice1 == dice2:
                player.leave_jail()
                observer.Event("update_state", f"{player.name} rolled doubles and got out of jail!")
                player.move(dice1 + dice2)
            else:
                turns = player.increment_jail_turns()
                if turns >= 3:
                    if player.money >= 50:
                        player.money -= 50
                        player.leave_jail()
                        observer.Event("update_state", f"{player.name} paid $50 to leave jail.")
                        player.move(dice1 + dice2)
                    else:
                        observer.Event("update_state", f"{player.name} couldn't pay bail. Stayed in jail.")
                else:
                    observer.Event("update_state", f"{player.name} did not roll doubles. Jail Turn {turns}/3.")
            return

        if not self._handle_roll_dice():
            return

        square = self._gameboard.get_square(player.position)
        money = player.money

        msg = f"{player.name} landed on {square}."

        observer.Event("update_state", msg)
        observer.Event("update_state_box", str(self._gameboard))
        observer.Event("update_card", player.position)




