"""
Sample code for SNRE refactoring demonstration
This file contains various code patterns that SNRE agents can optimize
"""

# Security issues for SecurityEnforcer to detect
password = os.environ.get("PASSWORD")
api_key = os.environ.get("API_KEY")

def vulnerable_query(user_id):
    """SQL injection vulnerability"""
    import sqlite3
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # Vulnerable to SQL injection
    cursor.execute("SELECT * FROM users WHERE id = ?" % user_id)
    return cursor.fetchall()

def unsafe_eval(user_input):
    """Dangerous eval usage"""
    return eval(user_input)

# Loop inefficiencies for LoopSimplifier to optimize
def inefficient_loops():
    """Various loop inefficiency patterns"""
    items = [1, 2, 3, 4, 5]

    # range(len()) pattern
    result1 = []
    for i in range(len(items)):
        result1.append(items[i] * 2)

    # Nested loop with append
    matrix = [[1, 2], [3, 4], [5, 6]]
    flattened = []
    for row in matrix:
        for item in row:
            flattened.append(item)

    # Unnecessary temp variables
    temp_sum = 0
    for item in items:
        temp_value = item * 2
        temp_sum += temp_value

    return result1, flattened, temp_sum

# Pattern optimization opportunities
def pattern_issues():
    """Code patterns that can be optimized"""
    items = [1, 2, 3, 4, 5]

    # Can be converted to list comprehension
    squared = []
    for item in items:
        squared.append(item ** 2)

    # Ternary operator opportunity
    def check_positive(x):
        if x > 0:
            return "positive"
        else:
            return "negative"

    # Unnecessary variable assignment
    result = None
    temp_data = None

    return squared, check_positive, result, temp_data

# Complex nested function for complexity analysis
def complex_function(data, threshold, mode):
    """Overly complex function with high cyclomatic complexity"""
    result = []

    if data is None:
        return None

    for item in data:
        if isinstance(item, dict):
            if 'value' in item:
                if item['value'] > threshold:
                    if mode == 'strict':
                        try:
                            processed = item['value'] * 2
                            if processed < 100:
                                result.append(processed)
                            else:
                                if mode == 'strict':
                                    continue
                                else:
                                    result.append(100)
                        except Exception:
                            continue
                    else:
                        result.append(item['value'])
                else:
                    if mode == 'lenient':
                        result.append(item['value'] / 2)
            else:
                continue
        else:
            if isinstance(item, (int, float)):
                result.append(item)

    return result

# Performance issues
def performance_problems():
    """Code with performance issues"""
    data = list(range(1000))

    # Inefficient membership testing with list
    found_items = []
    search_list = [1, 5, 10, 15, 20]  # Should use set
    for item in data:
        if item in search_list:  # O(n) lookup in list
            found_items.append(item)

    # Redundant computation in loop
    results = []
    expensive_value = sum(range(100))  # Computed every iteration
    for i in range(10):
        results.append(i * expensive_value)

    return found_items, results

if __name__ == "__main__":
    print("Sample code for SNRE refactoring")
    print("Run: python main.py cli start --path examples/sample_refactor.py --agents security_enforcer,pattern_optimizer,loop_simplifier")
