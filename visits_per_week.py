import argparse
from datetime import datetime
from typing import Tuple, Dict, Set


class Counter:
    """ Class used to count, with an integer and a public method for incrementation. """

    __slots__ = 'count',

    def __init__(self):
        self.count = 0

    def increment(self):
        self.count += 1


class User:
    """ User, represented by a name and a group number. """

    __slots__ = 'name', 'group'

    def __init__(self, name, group):
        # type: (str, int) -> None
        self.name = name
        self.group = group

    @property
    def identifier(self):
        return self.name, self.group

    def __str__(self):
        return '%s #%s' % (self.name, self.identifier)

    def __hash__(self):
        return hash(self.identifier)

    def __eq__(self, other):
        return self.identifier == other.identifier

    def __lt__(self, other):
        return self.identifier < other.identifier


class Week:
    """ A week, identified by a year and a week number in the year (from 1 to 52).
        Handle a dictionary called "daily_presences" to map a date (year, month day number)
        to a set of users who passed at that date.
    """

    __slots__ = 'year', 'number', 'daily_presences'

    def __init__(self, year, number):
        # type: (int, int) -> None
        self.year = year
        self.number = number
        self.daily_presences = {}  # type: Dict[datetime, Set[User]]

    @property
    def identifier(self):
        return self.year, self.number

    def __str__(self):
        """ Describe bound dates of the week found in daily presences. """
        if len(self.daily_presences) == 1:
            date = next(iter(self.daily_presences))
            return '(only %s)' % ('/'.join(str(val) for val in (date.year, date.month, date.day)))

        min_date = min(self.daily_presences)
        max_date = max(self.daily_presences)
        common_pieces = []
        from_pieces = []
        to_pieces = []
        for field in ('year', 'month', 'day'):
            min_val = getattr(min_date, field)
            max_val = getattr(max_date, field)
            if min_val == max_val:
                common_pieces.append(str(min_val))
            else:
                from_pieces.append(str(min_val))
                to_pieces.append(str(max_val))
        return '(%s from %s to %s)' % (
            '/'.join(common_pieces), '/'.join(from_pieces), '/'.join(to_pieces))

    def __hash__(self):
        return hash(self.identifier)

    def __eq__(self, other):
        return self.identifier == other.identifier

    def __lt__(self, other):
        return self.identifier < other.identifier


class WeekSet:
    """ Set of weeks. Used to classify user passages per week. """

    def __init__(self):
        # Dictionary mapping a week identifier to a week.
        self.weeks = {}  # type: Dict[Tuple[int, int], Week]

    def __len__(self):
        return len(self.weeks)

    def __iter__(self):
        # Iterate over weeks in ascending order of weeks.
        return iter(sorted(self.weeks.values()))

    def add_passage(self, date, user):
        # type: (datetime, User) -> None
        """ Add a user passage to week set. Create a new week instance if associated week
            is not already in the set.
            :param date: date when user passed.
            :param user: user to add.
        """
        week_identifier = date.isocalendar()[:2]
        if week_identifier in self.weeks:
            week = self.weeks[week_identifier]
        else:
            week = Week(*week_identifier)
            self.weeks[week_identifier] = week
        # Reduce passage date precision to day number only.
        passage_date = datetime(year=date.year, month=date.month, day=date.day)
        # Use simplified date to register passage into week daily presences.
        week.daily_presences.setdefault(passage_date, set()).add(user)


def parse_name_and_group(description_2):
    # type: (str) -> Tuple[str, int]
    """ Split description #2 from CSV input file into user name (string) and user group (integer).
        :param description_2: description to parse
        :return: a tuple containing (user name, user group).
            If user group cannot be parsed, return (description_2, -1).
    """
    index_of_sharp = description_2.rfind('#')
    if 0 < index_of_sharp < len(description_2) - 1:
        name = description_2[:index_of_sharp].strip()
        try:
            group = int(description_2[(index_of_sharp + 1):].strip())
        except ValueError:
            group = -1
        return name, group
    return description_2, -1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', '-i',
                        help='CSV input file containing security system output.')
    parser.add_argument('--output', '-o',
                        help='Name of output CSV file to be generated.')
    parser.add_argument('--encoding', '-e', default='utf-16',
                        help='Encoding of input CSV file (default "utf-16"). '
                             'Will be also used for output file.')
    parser.add_argument('--separator', '-s', default=',',
                        help='Column separator for input CSV file (default ","). '
                             'Will be also used for output file.')

    args = parser.parse_args()
    week_set = WeekSet()

    print('# Parsing input', args.input)
    with open(args.input, encoding=args.encoding) as file:
        line_iterator = iter(file)
        # Skip first line.
        next(line_iterator)
        # Parse next lines.
        for line_number, line in enumerate(line_iterator):
            columns = line.split(',')
            date = datetime.fromisoformat(columns[1].strip())
            name, group = parse_name_and_group(columns[7].strip())
            user = User(name, group)
            week_set.add_passage(date, user)
            if (line_number + 1) % 10000 == 0:
                print('# Read', line_number + 1, 'entries.')
    print('# Parsing finished,', line_number + 1, 'entries.')

    # Count presences per week for each user and generate header names for output CSV file.
    print('# Found', len(week_set), 'week(s). Count passages per week for each user.')
    headers = ['Name', 'Group']
    user_to_week_to_count = {}
    for i, week in enumerate(week_set):  # type: (int, Week)
        week_name = 'Week %d %s' % (i + 1, week)
        headers.append(week_name)
        for users in week.daily_presences.values():
            for user in users:  # type: User
                user_to_week_to_count.setdefault(user, {}).setdefault(week, Counter()).increment()

    print('# Generating output', args.output)
    with open(args.output, 'w', encoding=args.encoding) as file:
        # Write headers.
        file.write(args.separator.join(headers))
        file.write('\n')
        # Write lines, one line per user.
        # Users are sorted in raw alphabetical orders.
        for user, week_to_count in sorted(user_to_week_to_count.items()):
            line = [user.name, str(user.group)]
            for week in week_set:
                line.append(str(week_to_count.get(week, Counter()).count))
            file.write(args.separator.join(line))
            file.write('\n')


if __name__ == '__main__':
    main()
