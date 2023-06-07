#!/usr/bin/env python3.10

"""


1. this is a monir change [#001]


Other ways to get closer on a guess:
    - analyze most impactful (not just most probable) letters
        --> this helps make a good guess
        --> Can not do, requires knowledge of the solution to assess impact
    - choose words that are more common (based on a word list that
        lists words in order of probability)  --> helps make a good guess
    - make anagrams from most probable letters to use as guesses

---

1. Same old, same old.
    ==> if several 'best guesses' have same score, choose one randomly

---
2. The rhymes problem.

    E.g., solution is "VINES"
        List of possibilities has 11 items
        ['BINES', 'CINES', 'FINES', 'KINES', 'MINES', 'NINES', 'PINES', 'SINES', 'VINES', 'WINES', 'ZINES']
        Most likely remaining letters: BCFKMPVWZ
        Most valued letters: BCFKMNPSVWZ
        Most valued guesses:   CINES  PINES  MINES  BINES

    Solution is 'GEARS'
        List of possibilities has 11 items
        ['BEARS', 'DEARS', 'FEARS', 'GEARS', 'HEARS', 'NEARS', 'PEARS', 'REARS', 'SEARS', 'WEARS', 'YEARS']
        Most likely remaining letters: BDFGHNPWY
        Most valued letters: BDFGHNPRSWY
        Most valued guesses:   NEARS  DEARS  YEARS  PEARS


    Ideas:
        - recognize this as a case.  E.g.
            Entire possibles list (more than 2 in list)
            has all letters same except one.
        - recognize when entire (non-zero) list of 'most valued letters' is
            all same (e.g. "1", though maybe otherwise?)
        In which case anagram something that includes as many as possible
            of the changeable letter with anything else, and ask that.

3. Obscure guesses.

    The machine guesses an obscure word rather than a common one.
    E.g.:  solution is 'RENEW':
        List of possibilities has 6 items
        ['REFER', 'REHEM', 'REMEN', 'REMEX', 'RENEW', 'REPEG']
        Most likely remaining letters: MNFGHPWX
        Most valued letters: MNFGHPRWX
        Most valued guesses:   REMEN  RENEW  REHEM  REPEG
        --------------------------
        I guess: REMEN
    What to do:
        Where 'most valued guesses' all have same score, choose the
        most common.  (Requires a list of word frequencies)


----
Global variables:
ALPHABET
master_list (immutable once loaded from file)
position_known[0..4] -> None or the letter this position is known to be
position_not[0..4] -> letters known not to be in this position (or '')
alpha_status['A'..'Z'] -> MISS, HIT, PARTIAL, or (?)None

"""

import re
import random
from pprint import pprint
import sys


##spelling_dictionary = []

SOLUTIONS_FILE = 'wordle-solutions-list.txt'    # Solution will be selected from this
GUESSES_FILE = 'wordle-dictionary.txt'    # Guesses must be in this list
FREQUENCY_FILE = 'wordle-frequency-dictionary.txt'

ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

class Knowledge():
    """State of a current (or prospective) guess."""

    # Single-character values for what we know of a single letter.
    HIT = '*'       # Can't eval to False
    PARTIAL = '?'   # Can't eval to False
    MISS = '-'      # Can't eval to False
    UNKNOWN = ' '

    def __init__(self, wordlist:list[str]) -> None:
        self.position_knwon = {}
        self.position_known = {} # 0..4, val = False or the letter
        self.position_not = {}   # 0..4, val = str of letters known not to be at this pos
        self.alpha_status = {}   # A..Z, val = HIT, PARTIAL, MISS, or UNKNOWN
        self.alpha_known = ''    # str of letters known to be in word (naive about dups)
        self.alpha_count = {}    # A..Z, val = min occurances of this letter in solution
        self.alpha_not = ''      # str of letters known not to be in word
        for i in range(0,5):
            self.position_known[i] = False
            self.position_not[i] = ''
        for ch in ALPHABET:
            self.alpha_status[ch] = Knowledge.UNKNOWN
            self.alpha_count[ch] = 0
        self.alpha_not = ''
        self.wordlist = wordlist

    def update(self:object, guess: str, result:str):
        """Updates what's knowns based on the guess and the result."""

        for this in range(0,5):
            this_letter = guess[this]
            match result[this]:
                case Knowledge.HIT:
                    self.position_known[this] = this_letter
                    self.alpha_status[this_letter] = Knowledge.HIT
                case Knowledge.MISS:
                    self.position_not[this] += this_letter
                case Knowledge.PARTIAL:
                    self.position_not[this] += this_letter
                    if self.alpha_status[this_letter] != Knowledge.HIT:
                        self.alpha_status[this_letter] = Knowledge.PARTIAL
                case _:
                    print( f"Bad case value {guess[this]=}, {result[this]=}, {this=}" )

        # If a letter in guess is a MISS and the same letter isn't
        # already known to be PARTIAL or HIT, then we know that
        # letter does not occur at all.
        for this in range(0,5):
            if result[this] == Knowledge.MISS and self.alpha_status[guess[this]] not in Knowledge.HIT+Knowledge.PARTIAL:
                self.alpha_status[guess[this]] = Knowledge.MISS

        # What letters do we know for sure are/aren't in the word?
        # FIXME: Reminder that alpha_known is naive about possible duplicates
        self.alpha_not = ''
        self.alpha_known = ''
        for ch in ALPHABET:
            if self.alpha_status[ch] == Knowledge.MISS:
                self.alpha_not += ch
            elif self.alpha_status[ch] in Knowledge.HIT + Knowledge.PARTIAL:
                self.alpha_known += ch

        # Count number of occurances of a given letter
        multi = {}
        for pos in range(0,5):
            myletter = guess[pos]
            if result[pos] in Knowledge.HIT + Knowledge.PARTIAL:
                if myletter not in multi:
                    multi[myletter] = 1
                else:
                    multi[myletter] += 1
        for letter, count in multi.items():
            if count > self.alpha_count[letter]:
                self.alpha_count[letter] = count

def merge_lists( list1:list[str], list2:list[str] ) -> list[str]:
    """Adds anything in list2 but not list1 to list1"""
    # The order of list1 is preserved in the returned list.
    for w in list2:
        if w not in list1:
            list1.append(w)
    return list1

def load_wordlist( wordfile:str ) -> list[str]:
    """Reads a word list from file, preserving order."""
    # Skips blank lines and lines that start with '#'

    # Read file into wordlist.
    f = open( wordfile )
    lst = f.readlines()
    f.close()
    lst = [x.strip().upper() for x in lst]
    r_good = re.compile( '^[A-Z]{5}$')
    r_ignore = re.compile(  '^\s*(#.*)*$' ) # blanks & comments
    newlist = []
    for w in lst:
        if r_good.match(w):
            newlist.append(w)
        elif not r_ignore.match(w):
            print( f"Word {w} rejected from list in {wordfile}")
    return newlist

def anagram_strict( wordlist:list[str], letters:str ) -> list[str]:
    """Return a list of words that are made up of & use all of [letters]."""
    r = re.compile( '^[' + letters.upper() + ']+$')
    return list(filter(r.match, wordlist))

def anagram_loose( wordlist:list[str], letters:str ) -> list[str]:
    """Return a list of words that include all [letters] (& maybe others)."""
    letters = letters.upper()
    r = re.compile( '^[' + letters.upper() + ']+$')
    newlist = list(filter(r.match, wordlist))
    for ltr in letters:
        r = re.compile( ltr )
        newlist = list(filter(r.search, newlist))
    return newlist

def fishing_guess():
    """Return a 'best' next guess to fish out more info."""
    pass

def calculate_guess(wordlist:list, known:Knowledge):
    """Calculate a guess."""
    valued_words = most_valued_words(wordlist,known)
    guess = valued_words[0]
    print( f"\n--------------------------\nI guess: {guess}\n")
    return valued_words[0]

def ask_user_for_guess( dictionary:list[str]) -> str:
    """Ask for a guess, make sure it's in dictionary."""
    done = False
    while not done:
        myguess = input( 'Guess: ').upper().strip()
        if myguess in dictionary:
            done = True
        else:
            print( f"Word '{myguess}' not in dictionary.")
    return myguess

def swap_chr( s: str, c:chr, i:int) -> str:
    """Return s with c in position i."""
    before = s[:i]
    after = s[i+1:] if i < len(s)-1 else ''
    return before + c + after

def space_str(string:str) -> str:
    """Returns same str with spaces bewteen each character."""
    s = ''
    for c in string:
        s += c + ' '
    return s[:-1]

def test_guess( solution:str, guess:str ) -> str:
    """Returns result of matching guess against solution."""
    # Return is 5-character string of HIT, PARTIAL, MISS characters.
    # Watch for oddball case where solution contains multiples of a letter
    # and the guess does too.
    theresult = Knowledge.MISS * 5
    guess = guess.upper()
    # Look for perfect hits
    for pos in range(0,5):
        if guess[pos] == solution[pos]:
            theresult = swap_chr(theresult, Knowledge.HIT, pos)
            solution = swap_chr(solution, ' ', pos)
        ##print( f"1: {pos=}, {guess[pos]=}, {solution=}, {guess=}, {theresult=}")
    # Look for partials (unless was already a hit)
    # FIXME:
    #   Still gets it wrong if target has 2 letters same
    #   E..g. solution = START.  Guess 'BLUNT'
    #   NB: the error is in determining the result, not analysing it
    #   NB: the error is in this second loop
    for pos in range(0,5):
        if theresult[pos] == Knowledge.HIT:
            continue
        idx = solution.find(guess[pos])
        if idx != -1:
            theresult = swap_chr(theresult, Knowledge.PARTIAL, pos)
            solution = swap_chr(solution, ' ', idx)
        ##print( f"2: {pos=}, {guess[pos]=}, {idx=}, {solution=}, {guess=}, {theresult=}")
    return theresult

def print_guess_result( solution:str, guess:str, result:str, known:Knowledge, guess_history:list[str], spelling_dictionary:list[str]):
    """Print the current state of guesswork."""
    print( "\n\n\n")
    alpha_what = ''
    for c in ALPHABET:
        alpha_what += known.alpha_status[c]
    for s in guess_history:
        print( f"{space_str(s)}")
        print( f"{space_str(test_guess(solution, s))}\n")
    print( f"{space_str(guess)}     {space_str(ALPHABET)}")
    print( f"{space_str(result)}     {space_str(alpha_what)}")
    print( f"List of possibilities has {len(known.wordlist)} items")
    if len(known.wordlist) < 20:
        print(known.wordlist)
    ##print( f"Most likely letters: {count_frequences(mylist,'')}")
    print( f"Most likely remaining letters: "
            f"{count_frequences(known.wordlist,known.alpha_not+known.alpha_known)}")
    print( f"Most valued letters: {most_valued_letters(known)}")
    valued_words = most_valued_words(spelling_dictionary,known)
    print( f"Most valued guesses: ", end='')
    for idx in range(0,min(4,len(valued_words))):
        print( f"  {valued_words[idx]}", end='')
    print()

    # Show values for most-valued letters as a indicator of Rhyming Problem
    vl = valued_str( known.wordlist, ALPHABET, known.alpha_count)
    for ltr in sorted(vl.keys()):
        if vl[ltr] < 1:
            continue
        print( f"\t{ltr}: {vl[ltr]}")



    ##print( "Letter scores:")
    ##pprint( valued_str(known.wordlist, ALPHABET, known.alpha_count))

    print( f"Letters known yes: {known.alpha_known=}")
    print( f"Letters known not: {known.alpha_not=}")
    print( "Multiple letters: ", end='')

    for ch in ALPHABET:
        if known.alpha_count[ch] > 1:
            print( f"{ch}:{known.alpha_count[ch]} ", end='')
    print()

def prune_list( start_list:list[str], known:Knowledge ) -> list[str]:
    """Returns a word list, pruned to possible solutions."""
    # Make a reg expression, position by position
    re_str = ''
    for pos in range(0,5):
        # Do we know the very letter this must be?
        if known.position_known[pos]:
            re_str += known.position_known[pos]
        # Do we know things this position cannot be?
        elif known.position_not[pos] or known.alpha_not:
            re_str += '[^' + ''.join(sorted(set(known.position_not[pos] + known.alpha_not))) + ']'
        # Otherwise we know nothing, use a wildcard.
        else:
            re_str += '.'
    r = re.compile( '^' + re_str + '$')
    ##print( f"Pruning on '^{re_str}$' ")
    pruned = list(filter(r.match, start_list))
    # Exclude words that don't contain required # of known letters
    for ltr in ALPHABET:
        if known.alpha_count[ltr] > 0:
            r_str = ltr
            for n in range(1,known.alpha_count[ltr]):
                r_str += '.*' + ltr
            r = re.compile( r_str )
            ##print( f"Pruning on '/{r_str}/' ")
            pruned = list(filter(r.search,pruned))
    return pruned

def fetch_random_solution( wordlist: list[str] ) -> str:
    """Returns a random solution from the wordlist."""
    return random.sample(wordlist, 1)[0]

def ask_user_for_solution( dictionary:list[str]) -> str:
    """Ask for a solution, make sure it's in dictionary."""
    done = False
    while not done:
        sol = input( 'What word will be the solution? ').upper().strip()
        if sol in dictionary:
            done = True
        else:
            yn = input( 'Word not in dictionary.  Use it anyway? ').upper().strip()
            if yn and yn[0] == 'Y':
                print("OK.  I'll add your word to the dictionary for this session.")
                done = True
    return sol

def is_solved(solution, guess) -> bool:
    """Returns True if it's solved."""
    return guess == solution


def valued_str( wordlist: list[str], alpha:str, alpha_known_count:dict[str:int] ) -> dict[str:int]:
    """Returns dict of letter:value for alpha letters in wordlist."""
    # Assigns each letter in alpha a value (measure of desirability) based
    # on its number of occurances in wordlist.  For letters already known, the
    # value per owrd of a letter's score is reduced by the # of letters known.
    ltr_count = {}
    words_with_ltr = {}
    for alpha_ltr in alpha:
        ltr_count[alpha_ltr] = 0
        words_with_ltr[alpha_ltr] = 0

    for alpha_ltr in alpha:
        for word in wordlist:
            if alpha_ltr in word:
                words_with_ltr[alpha_ltr] += 1

    for word in wordlist:
        for word_ltr in word:
            ltr_count[word_ltr] += 1

    # Reduce score for each letter that we already know.
    for alpha_ltr in alpha:
        if alpha_ltr in alpha_known_count:
            ltr_count[alpha_ltr] -= max(0,
                max(0,alpha_known_count[alpha_ltr])
                * words_with_ltr[alpha_ltr] )

    return ltr_count


def valued_list(wordlist:list[str], known:Knowledge) -> dict[str:int]:
    """Returns dict of word:value given wordlist and dict of letter values."""
    multi_penalty = 0
    letter_val = valued_str(wordlist, ALPHABET, known.alpha_count)
    vlist = {}
    for word in known.wordlist:
        vlist[word] = 0
        for idx in range(0,5):
            ltr = word[idx]
            # Apply a penalty to letters that are already in the word.
            if word.find(ltr,0,idx) < 0:
                vlist[word] += letter_val[ltr]
            else:
                vlist[word] += letter_val[ltr] * multi_penalty
    return vlist

def most_valued_words(wordlist:list[str], known:Knowledge) -> list[str]:
    """Returns list of words, most valued first."""
    word_val = valued_list(wordlist, known)
    val_word_dict = flip_dictionary( word_val)
    val_word_list = []
    for val in reversed(sorted(val_word_dict)):
        val_word_list += [x for x in val_word_dict[val]]
    return val_word_list

def most_valued_letters(known:Knowledge) -> str:
    """Return ordered string of highest-impact letters."""
    letter_val = valued_str(known.wordlist, ALPHABET, known.alpha_count)
    val_letter = flip_dictionary(letter_val)
    ltr_str = ''
    for val in reversed(sorted(val_letter)):
        if val < 1:
            break
        ltr_str += ''.join(val_letter[val])
    return ltr_str


def flip_dictionary( dict_in:dict ) -> dict[any:list[str]]:
    """Returns dict that has keys & values swapped."""
    # Since two input keys could have same value, the returned
    # dict has for values a list of all the keys that matched that value.
    flipped = {}
    for key, val in dict_in.items():
        if val not in flipped:
            flipped[val] = []
        flipped[val].append(key)
    return flipped


def count_frequences( wordlist:list[str], without:str ) -> str:
    """Returns a string of letters in wordlist starting with most freq."""

    ltrk = {}
    for ltr in ALPHABET:
        ltrk[ltr] = 0
    for w in wordlist:
        for ltr in ALPHABET:
            if ltr in w:
                ltrk[ltr] += 1
    # Reverse sort on frequency
    freq_dict = dict(sorted(ltrk.items(), key=lambda x: x[1], reverse=True))
    freq_str = ''
    for val in freq_dict:
        # Exclude the exclusion list, also letters with 0 or 1 frequency.
        if val not in without and ltrk[val]:
            freq_str += val
    return freq_str

def list_reduction( solution:str, testguess:str, testknown:Knowledge) -> int:
    """Return amount wordlist is reduced if testguess were guessed."""

    # FIXME: can't use this as it's "cheating" - that is, is requires
    # knowledge of the solution.  So.... nice try but no.
    start_size = len(testknown.wordlist)
    result = test_guess(solution, test_guess)
    testknown.update(test_guess, result)
    end_size = len(testknown.wordlist)
    return start_size - end_size

def does_the_human_guess() -> bool:
    """Returns True if computer generates a solution, False if humans do. """
    # Default is True (computer)
    if len(sys.argv) <= 1:
        return True
    thisarg = sys.argv[1].strip().upper()
    ##print(f"{sys.argv=}, {thisarg=}")
    target = 'HUMAN'[0:len(thisarg)]
    if target == thisarg:
        return False
    return True

def do_human_guessing(solution:str, spelling_dictionary:list[str]):
    """One game with the human guessing."""
    spelling_dictionary = merge_lists(spelling_dictionary, [solution])
    known = Knowledge(spelling_dictionary)

    print( f"There are {len(known.wordlist)} possible words.")
    print( f"Most likely letters: {count_frequences(known.wordlist,'')}")

    guess_history = []
    guess = ''
    while not is_solved(solution, guess):
        guess = ask_user_for_guess(spelling_dictionary)
        result = test_guess(solution, guess)
        known.update(guess, result)
        known.wordlist = prune_list(known.wordlist, known)
        if solution not in known.wordlist:
            print( "Have a problem! solution no longer in the maybe_words!")
        print_guess_result(solution, guess, result, known, guess_history, spelling_dictionary)
        guess_history.append(guess)
    print(f"Solved in {len(guess_history)} guesses.")


def do_computer_guessing(spelling_dictionary:list[str], frequency_dictionary:list[str]):
    """One game with the computer guessing."""
    solution = ask_user_for_solution(spelling_dictionary)
    # Make sure the solution is in the list of guessable words
    spelling_dictionary = merge_lists(spelling_dictionary, [solution])
    known = Knowledge(spelling_dictionary)

    print( f"There are {len(known.wordlist)} possible words.")
    print( f"Most likely letters: {count_frequences(known.wordlist,'')}")

    guess_history = []
    guess = ''
    while not is_solved(solution, guess):
        guess = calculate_guess(spelling_dictionary, known )
        result = test_guess(solution, guess)
        known.update(guess, result)
        known.wordlist = prune_list(known.wordlist, known)
        if solution not in known.wordlist:
            print( "Have a problem! solution no longer in the maybe_words!")
        print_guess_result(solution, guess, result, known, guess_history, spelling_dictionary)
        guess_history.append(guess)
    print(f"Solved in {len(guess_history)} guesses.")

def main():
    """Main."""
    solutions_list = load_wordlist(SOLUTIONS_FILE)
    spelling_dictionary = load_wordlist(GUESSES_FILE)
    frequency_dictionary = load_wordlist(FREQUENCY_FILE)
    ##analyze_list( spelling_dictionary)

    human_is_the_guesser = does_the_human_guess()
    finished = False
    while not finished:
        if human_is_the_guesser:
            do_human_guessing(
                    fetch_random_solution(solutions_list),
                    spelling_dictionary)
        else:
            do_computer_guessing(spelling_dictionary, frequency_dictionary)

if __name__ == '__main__':
    main()
