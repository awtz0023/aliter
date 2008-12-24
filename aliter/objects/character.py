from actor import Actor
from manager import Manager
from account import Accounts
from aliter.exceptions import InvalidItem


class Character(Actor):
    required = [
        "accountID", "charNum",
    ]
    optional = [
        ("id", None),
        ("job", 0),
        ("jobLevel", 1),
        ("zeny", 0),
        ("maxSP", 11),
        ("sp", 11),
        ("statusPoints", 0),
        ("skillPoints", 0),
        ("partyID", 0),
        ("guildID", 0),
        ("petID", 0),
        ("homunculusID", 0),
        ("mercenaryID", 0),
        ("hairStyle", 0),
        ("hairColor", 0),
        ("clothesColor", 0),
        ("viewWeapon", 1),
        ("viewShield", 0),
        ("viewHeadTop", 0),
        ("viewHeadMiddle", 0),
        ("viewHeadBottom", 0),
        ("saveMap", "new_zone01"),
        ("saveX", 53),
        ("saveY", 111),
        ("online", 0),
        ("fame", 0),
        ("guildPositionID", 0),
        ("guildTaxed", 0)
    ]
    saveData = [
        "id", "accountID", "charNum", "job", "jobLevel", "zeny", "maxSP",
        "sp", "statusPoints", "skillPoints", "partyID", "guildID", "petID",
        "homunculusID", "mercenaryID", "hairStyle", "hairColor",
        "clothesColor", "viewWeapon", "viewShield", "viewHeadTop",
        "viewHeadMiddle", "viewHeadBottom", "saveMap", "saveX", "saveY",
        "online", "fame", "guildPositionID", "guildTaxed"
    ]
    
    inventory = {}
    
    def __init__(self, **kwargs):
        self.required.extend(super(Character, self).required)
        self.optional.extend(super(Character, self).optional)
        self.saveData.extend(super(Character, self).saveData)
        super(Character, self).__init__(**kwargs)
        
        self.gameID = self.accountID
    
    def account(self):
        """
        Returns the character's account.
        """
        return Accounts.get(self.accountID)
    
    def guild(self):
        """
        Returns the character's guild.
        """
        from guild import Guilds
        return Guilds.get(self.guildID)
    
    def position(self):
        """
        Returns the character's guild.
        """
        from guild import GuildPositions
        return GuildPositions.get(self.guildPositionID)
    
    def loadInventory(self):
        from aliter.objects import Inventory, Items
        
        self.inventory = {}
        
        inventory = Inventory.getAll(characterID = self.id)
        
        equips = []
        items = []
        
        index = 2
        for stock in inventory:
            item = Items.get(stock.itemID)
            if item.equipLocations == None:
                items.append({
                    "index": index,
                    "itemID": item.id,
                    "type": item.type,
                    "identified": stock.identified,
                    "amount": stock.amount,
                    "card1": stock.card1,
                    "card2": stock.card2,
                    "card3": stock.card3,
                    "card4": stock.card4
                })
            else:
                # Crazy-ass client logic.
                card1 = stock.forger and 255 or stock.card1
                card2 = stock.forger and stock.element + (stock.very * 1280) or stock.card2
                card3 = stock.forger and (18928 + (stock.forger - 150000)) or stock.card3
                card4 = stock.forger and 2 or stock.card4
                
                equips.append({
                    "index": index,
                    "itemID": item.id,
                    "type": item.type,
                    "identified": stock.identified,
                    "equipLocations": item.equipLocations,
                    "equipPoint": stock.equipLocation,
                    "refine": stock.refine,
                    "card1": card1,
                    "card2": card2,
                    "card3": card3,
                    "card4": card4
                })
            
            self.inventory[index] = { "item": item, "stock": stock }
            
            index += 1
        
        if items:
            self.session.sendPacket(
                0x1ee,
                items = items
            )
        
        if equips:
            self.session.sendPacket(
                0xa4,
                equips = equips
            )
    
    def load(self):
        from aliter.event import Event
        Event.warp(self, self.saveX, self.saveY, self.saveMap)
    
    def save(self, map = None, x = None, y = None):
        from aliter.event import Event
        self.saveMap = map or self.map
        self.saveX = x or self.x
        self.saveY = y or self.y
        Characters.save(self)
        
    def hasItem(self, id = None, **kwargs):
        """
        Checks if the player has an item.
        
        You can either provide an ID or keyword arguments to check for.
        
        If an item is found in the character's inventory (only one keyword
        argument has to match), it will return the inventory value 
        (as { "item": item, "stock": stock }). Otherwise, False.
        """
        if id:
            check = [v for k, v in self.inventory.iteritems() if v["item"].id == id]
            if check:
                return check[0]
        
        for key, val in kwargs.iteritems():
            check = [v for k, v in self.inventory.iteritems() if getattr(v["item"], key) == val]
            if check:
                return check[0]
        
        return False
    
    def inventoryIndex(self, id = None, **kwargs):
        """
        Same as hasItem, but returns the index of the item in their inventory.
        """
        if id:
            check = [k for k, v in self.inventory.iteritems() if v["item"].id == id]
            if check:
                return check[0]
        
        for key, val in kwargs.iteritems():
            check = [k for k, v in self.inventory.iteritems() if getattr(v["item"], key) == val]
            if check:
                return check[0]
        
        return False
    
    def give(self, id = None, amount = 1, **kwargs):
        """
        Gives `amount` items to the player.
        """
        from item import Items
        from inventory import Inventory
        
        if id:
            item = Items.get(id)
        else:
            item = Items.get(**kwargs)
        
        if not item:
            raise InvalidItem
        
        inventory = Inventory.getAll(
            characterID = self.id
        )
        
        if item.equipLocations == None:
            # Do they already have this item?
            stock = Inventory.get(itemID = item.id)
            
            if stock and stock:
                stock.amount += int(amount)
                Inventory.save(stock)
            else:
                stock = Inventory.create(
                    characterID = self.id,
                    itemID = item.id,
                    amount = int(amount)
                )
            
            search = [k for k, v in self.inventory.iteritems() if v["item"].id == item.id]
            index = search and search[0] or len(inventory) + 2
            
            self.session.sendPacket(
                0xa0,
                index = index,
                amount = int(amount),
                itemID = item.id,
                identified = 1,
                broken = 0,
                refine = 0,
                card1 = 0,
                card2 = 0,
                card3 = 0,
                card4 = 0,
                equipLocations = item.equipLocations or 0,
                type = item.type,
                fail = 0
            )
            
            self.inventory[index] = { "item": item, "stock": stock }
        else:
            for x in xrange(int(amount)):
                stock = Inventory.create(
                    characterID = self.id,
                    itemID = item.id,
                    amount = 1
                )
                
                index = len(inventory) + 2 + x
                self.session.sendPacket(
                    0xa0,
                    index = index,
                    amount = 1,
                    itemID = item.id,
                    identified = 1,
                    broken = 0,
                    refine = 0,
                    card1 = 0,
                    card2 = 0,
                    card3 = 0,
                    card4 = 0,
                    equipLocations = item.equipLocations or 0,
                    type = item.type,
                    fail = 0
                )
                
                self.inventory[index] = { "item": item, "stock": stock }
    
    def takeItem(self, id = None, amount = 1, **kwargs):
        """
        Takes `amount` items from the player.
        """
        from inventory import Inventory
        
        index = self.inventoryIndex(id, **kwargs)
        item, stock = self.hasItem(id, **kwargs)
        if stock.amount <= amount:
            Inventory.delete(stock.id)
            del self.inventory[index]
        else:
            self.inventory[index]["stock"].amount -= amount
            stock.amount -= amount
            Inventory.save(stock)
        
        # FIXME: Update the client?
    
    def warp(self, map, x, y):
        """
        Mask for Event.warp
        """
        from aliter.event import Event
        
        Event.warp(self, x, y, map)

class CharacterManager(Manager):
    modelClass = Character
    cacheDict  = {}
    table  = "characters"
    schema = [
        "id", "accountID", "charNum", "name", "job", "baseLevel", "baseExp",
        "jobLevel", "jobExp", "zeny", "str", "agi", "vit", "int", "dex",
        "luk", "maxHP", "hp", "maxSP", "sp", "statusPoints", "skillPoints",
        "partyID", "guildID", "petID", "homunculusID", "mercenaryID",
        "hairStyle", "hairColor", "clothesColor", "viewWeapon", "viewShield",
        "viewHeadTop", "viewHeadMiddle", "viewHeadBottom", "map", "x", "y",
        "saveMap", "saveX", "saveY", "online", "fame", "guildPositionID",
        "guildTaxed"
    ]

Characters = CharacterManager()