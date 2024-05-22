import time
from collections import deque

from pprint import pprint


class Sudoku:
    def __init__(self, sudoku):
        self.grid = sudoku
        self.recent_requests = deque()

    def _limit_calls(self, base_delay=0.01, interval=10, threshold=5):
        current_time = time.time()
        self.recent_requests.append(current_time)
        num_requests = len([t for t in self.recent_requests if current_time - t < 10])

        if num_requests > 5:
            delay = 0.01 * (num_requests - 5 + 1)
            time.sleep(delay)

    def __str__(self):
        string_representation = "| - - - - - - - - - - - |\n"

        for i in range(9):
            string_representation += "| "
            for j in range(9):
                string_representation += str(self.grid[i][j])
                string_representation += " | " if j % 3 == 2 else " "

            if i % 3 == 2:
                string_representation += "\n| - - - - - - - - - - - |"
            string_representation += "\n"

        return string_representation

    def update_row(self, row, values):
        """Update the values of the given row."""
        self.grid[row] = values
    
    def update_column(self, col, values):
        """Update the values of the given column."""
        for row in range(9):
            self.grid[row][col] = values[row]

    def check_row(self, row, base_delay=0.01, interval=10, threshold=5):
        """Check if the given row is correct."""
        self._limit_calls(base_delay, interval, threshold)

        # Check row
        if sum(self.grid[row]) != 45 or len(set(self.grid[row])) != 9:
            return False

        return True

    def check_column(self, col, base_delay=0.01, interval=10, threshold=5):
        """Check if the given row is correct."""
        self._limit_calls(base_delay, interval, threshold)

        # Check col
        if sum([self.grid[row][col] for row in range(9)]) != 45 or len(set([self.grid[row][col] for row in range(9)])) != 9:
            return False

        return True

    def check_square(self, row, col, base_delay=0.01, interval=10, threshold=5):
        """Check if the given 3x3 square is correct."""
        self._limit_calls(base_delay, interval, threshold)

        # Check square
        if sum([self.grid[row+i][col+j] for i in range(3) for j in range(3)]) != 45 or len(set([self.grid[row+i][col+j] for i in range(3) for j in range(3)])) != 9:
            return False

        return True

    def check(self, base_delay=0.01, interval=10, threshold=5):
        """Check if the given Sudoku solution is correct.
        
        You MUST incorporate this method without modifications into your final solution.
        """
        
        for row in range(9):
            if not self.check_row(row, base_delay, interval, threshold):
                return False

        # Check columns
        for col in range(9):
            if not self.check_column(col, base_delay, interval, threshold):
                return False

        # Check 3x3 squares
        for i in range(3):
            for j in range(3):
                if not self.check_square(i*3, j*3, base_delay, interval, threshold):
                    return False

        return True
    

    # my function to get sudoku line
    def get_line(self, row):
        return self.grid[row]
    

    def get_cell(self, row, col):
        return self.grid[row][col]
    

    def get_sudoku(self) -> list[list[int]]:
        return self.grid
    

    def update_cell(self, row, col, value):
        self.grid[row][col] = value
    

    def update_sudoku(self, new_sudoku):
        self.grid = new_sudoku

    # check if a line is valid
    def is_valid_line(self, line):
        return sum(line) == 45 and len(set(line)) == 9

    # my functions 
    def find_next_empty(self, puzzle):
        for r in range(9):
            for c in range(9):
                if puzzle[r][c] == 0:
                    return r, c
        return None, None


    def is_valid(self, puzzle, guess, row, col):
   
        row_vals = puzzle[row]
        if guess in row_vals:
            return False
        

        col_vals = [puzzle[i][col] for i in range(9)]
        if guess in col_vals:
            return False
        

        row_start = (row // 3) * 3
        col_start = (col // 3) * 3

        for r in range(row_start, row_start + 3):
            for c in range(col_start, col_start + 3):
                if puzzle[r][c] == guess:
                    return False
                
        return True


    def possible_numbers(self, puzzle, row, col):
        """Returns the possible numbers that can be placed in the given cell."""
        row_vals = puzzle[row]
        col_vals = [puzzle[i][col] for i in range(9)]

        row_start = (row // 3) * 3
        col_start = (col // 3) * 3
        square_vals = [puzzle[row_start + i][col_start + j] for i in range(3) for j in range(3)]

        return [i for i in range(1, 10) if i not in row_vals and i not in col_vals and i not in square_vals]    
    

    def generate_puzzles(self):
        """Generates all possible puzzles according to the possible numbers in each cell"""

        positions = {}
        for r in range(9):
            for c in range(9):
                if self.grid[r][c] == 0:
                    positions[(r, c)] = self.possible_numbers(self.grid, r, c)
        
        possible_puzzles = []
        # example_puzzle_list = self.get_sudoku()
        for r in range(9):
            for c in range(9):
                if self.grid[r][c] == 0:
                    for i in positions[(r, c)]:
                        new_puzzle = self.get_sudoku().copy()
                        new_puzzle[r][c] = i
                        possible_puzzles.append(new_puzzle)
                        # print('-+-'*10)
                        # pprint(new_puzzle)
        return possible_puzzles
    

    def solve_sudoku(self):
        # sudoku = Sudoku(puzzle)
        # if self.check():
        #     return True
        
        row, col = self.find_next_empty(self.grid)

        if row is None:
            return True

        for guess in range(1, 10):      
           

            if self.is_valid(self.grid, guess, row, col):
                self.grid[row][col] = guess 

                if self.solve_sudoku():
                    # print('achou', guess, row, col)
                    return True
            # print(self.grid)
            self.grid[row][col] = 0
        
        return False




if __name__ == "__main__":

    sudoku = Sudoku([
    [2, 3, 4, 1, 5, 6, 7, 8, 9],
    [1, 7, 9, 3, 2, 8, 4, 5, 6],
    [5, 6, 8, 4, 7, 9, 1, 3, 2],
    [3, 9, 1, 2, 4, 5, 6, 7, 8],
    [4, 2, 5, 6, 8, 7, 3, 9, 1],
    [6, 8, 7, 9, 1, 3, 2, 4, 5],
    [7, 5, 2, 8, 3, 1, 9, 6, 4],
    [8, 1, 6, 7, 9, 4, 5, 2, 3],
    [9, 4, 3, 5, 6, 2, 0, 0, 0]
    ])

    print(sudoku)

    if sudoku.check():
        print("Sudoku is correct!")
    else:
        print("Sudoku is incorrect! Please check your solution.")

    # sudoku.update_cell(0, 0, 2)
    # sudoku.update_cell(0, 1, 3)
    # sudoku.update_cell(0, 3, 4)
    # print(sudoku)

    starttime = time.time()
    pprint(sudoku.solve_sudoku())
    print("Time taken: ", time.time() - starttime)
    pprint(sudoku)

    # last time recorded: 9.760859489440918

