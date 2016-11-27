# This file is part of the sandals package, hosted on
# https://github.com/schollii/sandals.
#
# This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
# WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.
#
# Use, distribution and modification of this file is bound by the terms
# of the MIT (expat) license.
#
# Copyright (c) Oliver Schoenborn

"""
This file verifies a small portion of the SQLite API from Python's standard library.
For example, it confirms that fetch* functions return the following:
None from execute() of any but a SELECT statement
None from executescript() of any script that does not contain a SELECT statement
[] from executescript() of any script that contains at least one SELECT statement

"""

import sqlite3 as sql

import pytest


def sql_progress(*args, **kwargs):
    assert args == ()
    assert kwargs == {}
    print('progress', args, kwargs)


def get_sqlite_ver(sqlcon):
    ver = sqlcon.execute('SELECT SQLITE_VERSION()').fetchall()[0][0]
    assert ver is not None
    return ver


@pytest.fixture
def sqlcon():
    tracing = []
    with sql.connect(":memory:", ) as con:
        # con.set_progress_handler(sql_progress, 1)
        yield con


@pytest.fixture
def tracer(sqlcon):
    tracing = []

    def sql_trace_callback(statement):
        tracing.append(statement)

    sqlcon.set_trace_callback(sql_trace_callback)
    yield tracing


def test_execute(sqlcon, tracer):
    assert get_sqlite_ver(sqlcon) == "3.8.11"

    cursor = sqlcon.execute('CREATE TABLE Cars (Id INT, Name TEXT, Price INT)')
    assert cursor.fetchone() is None
    assert tracer == [
        'SELECT SQLITE_VERSION()',
        'CREATE TABLE Cars (Id INT, Name TEXT, Price INT)',
    ]

    tracer.clear()
    sqlcon.execute("INSERT INTO Cars VALUES(?,?,?)", (1, 'Audi', 52642))
    sqlcon.execute("INSERT INTO Cars VALUES(2,'Mercedes',57127)")
    sqlcon.execute("INSERT INTO Cars VALUES(3,'Skoda',9000)")
    sqlcon.execute("INSERT INTO Cars VALUES(4,'Volvo',29000)")
    sqlcon.execute("INSERT INTO Cars VALUES(5,'Bentley',350000)")
    sqlcon.execute("INSERT INTO Cars VALUES(6,'Citroen',21000)")
    sqlcon.execute("INSERT INTO Cars VALUES(7,'Hummer',41400)")
    cursor = sqlcon.execute("INSERT INTO Cars VALUES(8,'Volkswagen',21600)")
    assert cursor.fetchone() is None
    assert tracer == [
        'BEGIN ',
        "INSERT INTO Cars VALUES(1,'Audi',52642)",
        "INSERT INTO Cars VALUES(2,'Mercedes',57127)",
        "INSERT INTO Cars VALUES(3,'Skoda',9000)",
        "INSERT INTO Cars VALUES(4,'Volvo',29000)",
        "INSERT INTO Cars VALUES(5,'Bentley',350000)",
        "INSERT INTO Cars VALUES(6,'Citroen',21000)",
        "INSERT INTO Cars VALUES(7,'Hummer',41400)",
        "INSERT INTO Cars VALUES(8,'Volkswagen',21600)",
    ]

    tracer.clear()
    cursor = sqlcon.execute("SELECT Name FROM Cars")
    assert cursor.fetchall() == [('Audi',), ('Mercedes',), ('Skoda',), ('Volvo',), ('Bentley',), ('Citroen',), ('Hummer',), ('Volkswagen',)]

    pytest.raises(sql.Warning, sqlcon.execute, """\
        SELECT Name FROM Cars;
        INSERT INTO Cars VALUES(11,'Chrysler',54614);
        INSERT INTO Cars VALUES(12,'Hyundai',54615);
        """)

    assert tracer == [
        'SELECT Name FROM Cars'
    ]
    print('--------- Done with Cars table')


def test_executescript(sqlcon, tracer):
    # fetchone() always returns None (no record) and fetchall/many always return empty list (no records)

    cursor = sqlcon.executescript("""\
        CREATE TABLE Cars2(Id INT, Name TEXT, Price INT);
        INSERT INTO Cars2 VALUES(1,'Audi',52642);
        INSERT INTO Cars2 VALUES(2,'Mercedes',57127);
        INSERT INTO Cars2 VALUES(3,'Skoda',9000);
        INSERT INTO Cars2 VALUES(4,'Volvo',29000);
        INSERT INTO Cars2 VALUES(5,'Bentley',350000);
        INSERT INTO Cars2 VALUES(6,'Citroen',21000);
        INSERT INTO Cars2 VALUES(7,'Hummer',41400);
        INSERT INTO Cars2 VALUES(8,'Volkswagen',21600);
        """)
    assert cursor.fetchone() is None
    assert cursor.fetchmany() == []
    assert cursor.fetchall() == []
    assert tracer == [
        '        CREATE TABLE Cars2(Id INT, Name TEXT, Price INT);',
        "\n        INSERT INTO Cars2 VALUES(1,'Audi',52642);",
        "\n        INSERT INTO Cars2 VALUES(2,'Mercedes',57127);",
        "\n        INSERT INTO Cars2 VALUES(3,'Skoda',9000);",
        "\n        INSERT INTO Cars2 VALUES(4,'Volvo',29000);",
        "\n        INSERT INTO Cars2 VALUES(5,'Bentley',350000);",
        "\n        INSERT INTO Cars2 VALUES(6,'Citroen',21000);",
        "\n        INSERT INTO Cars2 VALUES(7,'Hummer',41400);",
        "\n        INSERT INTO Cars2 VALUES(8,'Volkswagen',21600);",
    ]

    # script is a statement:
    tracer.clear()
    cursor = sqlcon.executescript("SELECT Name FROM Cars2")
    assert cursor.fetchone() is None
    assert cursor.fetchmany() == []
    assert cursor.fetchall() == []
    # confirm there was in fact records:
    cursor = sqlcon.execute("SELECT Name FROM Cars2")
    assert cursor.fetchall() == [('Audi',), ('Mercedes',), ('Skoda',), ('Volvo',), ('Bentley',), ('Citroen',), ('Hummer',), ('Volkswagen',)]
    assert tracer == [
        'SELECT Name FROM Cars2',
        'SELECT Name FROM Cars2',
    ]

    # multi-statement script with a select:
    tracer.clear()
    cursor = sqlcon.executescript("""\
        INSERT INTO Cars2 VALUES(9,'Honda',54612);
        SELECT Name FROM Cars2;
        INSERT INTO Cars2 VALUES(10,'Dodge',54613);
    """)
    assert cursor.fetchone() is None
    assert cursor.fetchmany() == []
    assert cursor.fetchall() == []

    assert tracer == [
        "        INSERT INTO Cars2 VALUES(9,'Honda',54612);",
        '\n        SELECT Name FROM Cars2;',
        "\n        INSERT INTO Cars2 VALUES(10,'Dodge',54613);"]
    print('--------- Done with Cars2 table')


